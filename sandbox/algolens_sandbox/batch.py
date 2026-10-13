"""Run a batch of tests against one solution: compile (C++), then drive all tests in one jail.

Batch status values:
- ok             every test has a result (each with its own outcome)
- compile_error  C++ didn't compile; `compile_output` says why
- batch_timeout  the whole batch hit its wall-time budget; finished tests keep their results
- sandbox_error  the sandbox itself failed. Never a verdict on the code, and callers must
                 not count it toward or against verification.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from algolens_sandbox import jail

JOBS_DIR = Path("/jobs")
PYTHON = "/usr/local/bin/python3"
DRIVER = "/driver/driver.py"
# Not -I: it implies -E, which would ignore PYTHONHASHSEED and make set order random.
# -P -s -S give the rest of isolated mode; nsjail passes only the env vars we set.
DRIVER_FLAGS = ["-P", "-s", "-S"]
CPP_FLAGS = ["-std=c++17", "-O2", "-pipe", "-I/usr/local/include/algolens"]
COMPILE_LIMITS = jail.JailLimits(
    wall_s=30, cpu_s=30, mem_mb=1024, nproc=32, fsize_mb=64, tmp_mb=128
)
MAX_TESTS = 2000
MAX_SOURCE_BYTES = 200_000


class PerTestLimits(BaseModel):
    cpu_ms: int = Field(default=1000, ge=10, le=30_000)
    wall_ms: int = Field(default=3000, ge=10, le=60_000)
    mem_mb: int = Field(default=256, ge=64, le=1024)
    output_bytes: int = Field(default=1 << 20, ge=1024, le=1 << 20)


class TestCase(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    input: dict


class BatchRequest(BaseModel):
    language: Literal["python", "cpp"]
    source: str = Field(max_length=MAX_SOURCE_BYTES)
    entry: str = Field(default="", max_length=64)  # Python function name; unused for C++
    tests: list[TestCase] = Field(max_length=MAX_TESTS)
    per_test: PerTestLimits = PerTestLimits()
    batch_wall_s: int = Field(default=60, ge=1, le=300)

    @field_validator("entry")
    @classmethod
    def _entry_is_identifier(cls, v: str) -> str:
        if v and not v.isidentifier():
            raise ValueError("entry must be a Python identifier")
        return v


class TestResult(BaseModel):
    id: str
    outcome: Literal[
        "ok", "runtime_error", "timeout", "memory", "output_limit", "not_run", "setup_error"
    ]
    value: Any = None
    detail: str = ""
    cpu_ms: float = 0
    wall_ms: float = 0
    stdout: str = ""
    stderr: str = ""


class BatchResponse(BaseModel):
    status: Literal["ok", "compile_error", "batch_timeout", "sandbox_error"]
    detail: str = ""
    compile_output: str = ""
    results: list[TestResult] = []


def run_batch(req: BatchRequest) -> BatchResponse:
    if req.language == "python" and not req.entry:
        return BatchResponse(status="sandbox_error", detail="python batches need an entry")
    job = Path(tempfile.mkdtemp(dir=JOBS_DIR))
    try:
        work = job / "work"
        work.mkdir()
        if req.language == "cpp":
            failure = _compile(req.source, work)
            if failure:
                return failure
        else:
            (work / "solution.py").write_text(req.source)
        (work / "request.json").write_text(
            json.dumps(
                {
                    "language": req.language,
                    "entry": req.entry,
                    "per_test": req.per_test.model_dump(),
                    "tests": [t.model_dump() for t in req.tests],
                }
            )
        )
        return _drive(req, work)
    finally:
        shutil.rmtree(job, ignore_errors=True)


def _compile(source: str, work: Path) -> BatchResponse | None:
    (work / "solution.cpp").write_text(source)
    run = jail.run(
        [PYTHON, *DRIVER_FLAGS, DRIVER, "--exec",  # wrapper: no core dumps from the compiler
         "/usr/bin/g++", *CPP_FLAGS, "-o", "/work/a.out", "/work/solution.cpp"],
        work, COMPILE_LIMITS, writable_work=True,
    )  # fmt: skip
    if not run.started:
        return BatchResponse(status="sandbox_error", detail="compiler jail failed to start")
    if run.hit_time_limit:
        return BatchResponse(status="compile_error", detail="compilation timed out")
    if run.exit_code != 0 or not (work / "a.out").exists():
        output = run.stderr.decode(errors="replace").replace("/work/", "")
        return BatchResponse(status="compile_error", compile_output=output[-8000:])
    return None


def _drive(req: BatchRequest, work: Path) -> BatchResponse:
    per = req.per_test
    # The driver's own address space needs headroom above the per-test limit it enforces.
    limits = jail.JailLimits(
        wall_s=req.batch_wall_s, cpu_s=req.batch_wall_s, mem_mb=per.mem_mb + 256
    )
    stdout_cap = len(req.tests) * (per.output_bytes + (32 << 10)) + (1 << 20)
    run = jail.run([PYTHON, *DRIVER_FLAGS, DRIVER], work, limits, stdout_cap=stdout_cap)
    if not run.started:
        return BatchResponse(status="sandbox_error", detail="driver jail failed to start")

    by_id: dict[str, TestResult] = {}
    for line in run.stdout.decode(errors="replace").splitlines():
        try:
            result = TestResult.model_validate_json(line)
        except ValueError:
            return BatchResponse(status="sandbox_error", detail="driver produced malformed output")
        by_id[result.id] = result
    setup_failures = [r for r in by_id.values() if r.outcome == "setup_error"]
    if setup_failures:
        # Our own driver failed: report it as a sandbox fault, never as a verdict on the code.
        return BatchResponse(status="sandbox_error", detail=setup_failures[0].detail)
    results = [by_id.get(t.id) or TestResult(id=t.id, outcome="not_run") for t in req.tests]
    if len(by_id) == len(req.tests):
        return BatchResponse(status="ok", results=results)
    if run.hit_time_limit:
        done = len(by_id)
        return BatchResponse(
            status="batch_timeout",
            detail=f"batch exceeded {req.batch_wall_s} s after {done}/{len(req.tests)} tests",
            results=results,
        )
    # The driver stopped early without hitting the time limit: a sandbox fault, not a verdict.
    tail = run.stderr.decode(errors="replace")[-2000:]
    return BatchResponse(
        status="sandbox_error", detail=f"driver exited early ({run.exit_code}): {tail}"
    )
