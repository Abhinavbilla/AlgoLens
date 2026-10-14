"""Run a batch of tests against one solution: compile (C++), then drive all tests in one jail.

Batch status values:
- ok             every test has a result (each with its own outcome)
- compile_error  C++ didn't compile; `compile_output` says why
- compile_timeout the compiler ran out of time. Time-dependent (a busy machine can cause
                 it), so callers should retry before treating it as the code's fault.
- batch_timeout  the whole batch hit its wall-time budget; finished tests keep their results
- sandbox_error  the sandbox itself failed. Never a verdict on the code, and callers must
                 not count it toward or against verification.

run_trace() records one run for animation; see TraceResponse for its statuses.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from algolens_sandbox import jail
from algolens_sandbox.guard import check_traceable

JOBS_DIR = Path("/jobs")
PYTHON = "/usr/local/bin/python3"
DRIVER = "/driver/driver.py"
# Not -I: it implies -E, which would ignore PYTHONHASHSEED and make set order random.
# -P -s -S give the rest of isolated mode; nsjail passes only the env vars we set.
DRIVER_FLAGS = ["-P", "-s", "-S"]
# Must match the flags algolens.h.gch is built with in the Dockerfile, or the precompiled
# header is ignored; -Winvalid-pch makes that visible in the compiler output.
CPP_FLAGS = ["-std=c++17", "-O2", "-pipe", "-Winvalid-pch", "-I/usr/local/include/algolens"]
COMPILE_LIMITS = jail.JailLimits(
    wall_s=60, cpu_s=60, mem_mb=1024, nproc=32, fsize_mb=64, tmp_mb=128
)
MAX_TESTS = 2000
MAX_SOURCE_BYTES = 200_000


class PerTestLimits(BaseModel):
    cpu_ms: int = Field(default=1000, ge=10, le=30_000)
    wall_ms: int = Field(default=3000, ge=10, le=60_000)
    mem_mb: int = Field(default=256, ge=64, le=1024)
    output_bytes: int = Field(default=1 << 20, ge=1024, le=1 << 20)
    # Only used by traced tests, which only run_trace() creates.
    max_frames: int = Field(default=5000, ge=1, le=20_000)
    trace_output_bytes: int = Field(default=16 << 20, ge=1024, le=32 << 20)


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
    trace: dict | None = None


class BatchResponse(BaseModel):
    status: Literal["ok", "compile_error", "compile_timeout", "batch_timeout", "sandbox_error"]
    detail: str = ""
    compile_output: str = ""
    results: list[TestResult] = []


def run_batch(req: BatchRequest) -> BatchResponse:
    return _run(req, [t.model_dump() for t in req.tests])


def _run(req: BatchRequest, tests: list[dict]) -> BatchResponse:
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
                    "tests": tests,
                }
            )
        )
        return _drive(req, work, tests)
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
        return BatchResponse(status="compile_timeout", detail="compilation timed out")
    if run.exit_code != 0 or not (work / "a.out").exists():
        output = run.stderr.decode(errors="replace").replace("/work/", "")
        return BatchResponse(status="compile_error", compile_output=output[-8000:])
    return None


def _drive(req: BatchRequest, work: Path, tests: list[dict]) -> BatchResponse:
    per = req.per_test
    # The driver's own address space needs headroom above the per-test limit it enforces.
    limits = jail.JailLimits(
        wall_s=req.batch_wall_s, cpu_s=req.batch_wall_s, mem_mb=per.mem_mb + 256
    )
    per_result = [
        (per.trace_output_bytes if t.get("trace") else per.output_bytes) + (32 << 10) for t in tests
    ]
    stdout_cap = sum(per_result) + (1 << 20)
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
    results = [by_id.get(t["id"]) or TestResult(id=t["id"], outcome="not_run") for t in tests]
    if len(by_id) == len(tests):
        return BatchResponse(status="ok", results=results)
    if run.hit_time_limit:
        done = len(by_id)
        return BatchResponse(
            status="batch_timeout",
            detail=f"batch exceeded {req.batch_wall_s} s after {done}/{len(tests)} tests",
            results=results,
        )
    # The driver stopped early without hitting the time limit: a sandbox fault, not a verdict.
    tail = run.stderr.decode(errors="replace")[-2000:]
    return BatchResponse(
        status="sandbox_error", detail=f"driver exited early ({run.exit_code}): {tail}"
    )


# --- tracing ----------------------------------------------------------------------------------


class TraceRequest(BaseModel):
    source: str = Field(max_length=MAX_SOURCE_BYTES)
    entry: str = Field(min_length=1, max_length=64)
    input: dict
    cpu_ms: int = Field(default=5000, ge=10, le=30_000)  # tracing is ~10-50x slower
    mem_mb: int = Field(default=512, ge=64, le=1024)
    max_frames: int = Field(default=5000, ge=1, le=20_000)

    @field_validator("entry")
    @classmethod
    def _entry_is_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError("entry must be a Python identifier")
        return v


class TraceResponse(BaseModel):
    """status:
    ok            `trace` is a faithful recording; `value` matches the untraced run
    rejected      the source failed the traceability check (`problems` says why)
    runtime_error / timeout / memory / output_limit
                  the *untraced* run failed this way on this input: nothing to animate
    trace_failed  the untraced run was fine but the traced one hit a limit (too slow or too
                  large to record); try a smaller input
    mismatch      traced and untraced results differ: recording changed the behaviour.
                  Never animate this.
    sandbox_error the sandbox itself failed; not a verdict on the code
    """

    status: Literal[
        "ok", "rejected", "runtime_error", "timeout", "memory", "output_limit",
        "trace_failed", "mismatch", "sandbox_error",
    ]  # fmt: skip
    detail: str = ""
    problems: list[str] = []
    value: Any = None
    trace: dict | None = None


def run_trace(req: TraceRequest) -> TraceResponse:
    problems = check_traceable(req.source)
    if problems:
        return TraceResponse(status="rejected", problems=problems, detail=problems[0])
    wall_ms = min(req.cpu_ms * 3, 60_000)
    batch = BatchRequest(
        language="python",
        source=req.source,
        entry=req.entry,
        tests=[],
        per_test=PerTestLimits(
            cpu_ms=req.cpu_ms, wall_ms=wall_ms, mem_mb=req.mem_mb, max_frames=req.max_frames
        ),
        batch_wall_s=min(2 * wall_ms // 1000 + 10, 300),
    )
    # The same input untraced and traced, in one jail: the results must agree.
    tests = [
        {"id": "untraced", "input": req.input},
        {"id": "traced", "input": req.input, "trace": True},
    ]
    resp = _run(batch, tests)
    if resp.status != "ok":
        status = "sandbox_error" if resp.status == "sandbox_error" else "trace_failed"
        return TraceResponse(status=status, detail=resp.detail)
    return _judge(*resp.results)


def _judge(plain: TestResult, traced: TestResult) -> TraceResponse:
    if plain.outcome != "ok":
        return TraceResponse(status=plain.outcome, detail=plain.detail)
    if traced.outcome != "ok" or traced.trace is None:
        return TraceResponse(status="trace_failed", detail=traced.detail or "no trace produced")
    if traced.value != plain.value:
        return TraceResponse(
            status="mismatch",
            detail=f"traced result {traced.value!r} != untraced result {plain.value!r}",
        )
    return TraceResponse(status="ok", value=plain.value, trace=traced.trace)


class TraceCheckRequest(BaseModel):
    """Recording integrity for many inputs at once (spec: recording must not change the
    result on any test input). Returns per-input statuses, not the recordings."""

    source: str = Field(max_length=MAX_SOURCE_BYTES)
    entry: str = Field(min_length=1, max_length=64)
    inputs: list[dict] = Field(max_length=MAX_TESTS // 2)
    cpu_ms: int = Field(default=2000, ge=10, le=30_000)
    mem_mb: int = Field(default=512, ge=64, le=1024)
    max_frames: int = Field(default=5000, ge=1, le=20_000)
    batch_wall_s: int = Field(default=240, ge=1, le=300)

    @field_validator("entry")
    @classmethod
    def _entry_is_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError("entry must be a Python identifier")
        return v


class TraceCheckResult(BaseModel):
    status: str  # same statuses as TraceResponse, per input
    detail: str = ""
    frames: int = 0
    truncated: str | None = None


class TraceCheckResponse(BaseModel):
    status: Literal["ok", "rejected", "batch_timeout", "sandbox_error"]
    detail: str = ""
    problems: list[str] = []
    results: list[TraceCheckResult] = []


def run_trace_check(req: TraceCheckRequest) -> TraceCheckResponse:
    problems = check_traceable(req.source)
    if problems:
        return TraceCheckResponse(status="rejected", problems=problems, detail=problems[0])
    batch = BatchRequest(
        language="python", source=req.source, entry=req.entry, tests=[],
        per_test=PerTestLimits(cpu_ms=req.cpu_ms, wall_ms=min(req.cpu_ms * 3, 60_000),
                               mem_mb=req.mem_mb, max_frames=req.max_frames),
        batch_wall_s=req.batch_wall_s,
    )  # fmt: skip
    tests = []
    for i, inp in enumerate(req.inputs):
        tests.append({"id": f"u{i}", "input": inp})
        tests.append({"id": f"t{i}", "input": inp, "trace": "summary"})
    resp = _run(batch, tests)
    if resp.status in ("sandbox_error", "compile_error"):
        return TraceCheckResponse(status="sandbox_error", detail=resp.detail)
    results = []
    for plain, traced in zip(resp.results[::2], resp.results[1::2], strict=True):
        if plain.outcome == "not_run" or traced.outcome == "not_run":
            results.append(TraceCheckResult(status="not_run"))
            continue
        judged = _judge(plain, traced)
        summary = traced.trace or {}
        results.append(TraceCheckResult(status=judged.status, detail=judged.detail,
                                        frames=summary.get("frames", 0),
                                        truncated=summary.get("truncated")))  # fmt: skip
    status = "batch_timeout" if resp.status == "batch_timeout" else "ok"
    return TraceCheckResponse(status=status, detail=resp.detail, results=results)
