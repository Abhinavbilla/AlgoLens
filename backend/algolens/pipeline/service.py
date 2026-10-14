"""Submitting a pasted problem, processing it as a job, and storing the result (plan §4, §6).

Privacy: the pasted text lives only in the job's payload while the job waits, and is removed
from the row as soon as the worker picks it up (the worker also strips it from any job that
ends, whatever happened). Problems are stored and cached by a hash of the text, never the
text itself. The cache key also includes the system version, so changing the app, a prompt
or a model setting gives fresh results.
"""

import hashlib
import logging
import os
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from algolens import __version__
from algolens.ai.budget import Budget
from algolens.ai.client import (
    ENDPOINTS,
    AIClient,
    client_from_settings,
    parse_role,
    roles_fingerprint,
)
from algolens.config import get_settings
from algolens.db.models import Approach, Job, Problem, Run
from algolens.pipeline.prompts import prompt_set_hash
from algolens.pipeline.solve import SolveResult, solve
from algolens.sandbox.client import SandboxClient

log = logging.getLogger("algolens.pipeline")

MAX_TEXT = 10_000
CACHEABLE = ("done", "rejected")  # a "failed" run (e.g. budget) is retried on resubmission
KEY_ENV = {**{p: e for p, (_, e) in ENDPOINTS.items()}, "anthropic": "ANTHROPIC_API_KEY"}


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def system_version(ai: AIClient | None = None) -> str:
    roles = (ai or client_from_settings()).roles
    fp = hashlib.sha256(roles_fingerprint(roles).encode()).hexdigest()[:12]
    return f"{__version__}:{prompt_set_hash()}:{fp}"


def missing_keys(ai: AIClient | None = None) -> list[str]:
    """API keys the configured roles need but the environment doesn't have."""
    roles = (ai or client_from_settings()).roles
    needed = {
        KEY_ENV[parse_role(spec)[0]] for spec in roles.values() if not spec.startswith("fake:")
    }
    return sorted(k for k in needed if not os.environ.get(k))


def submit(session: Session, text: str, ai: AIClient | None = None) -> dict:
    """{"problem_id": ...} for a cached result, else {"job_id": ...} (new or already queued)."""
    h, version = text_hash(text), system_version(ai)
    cached = session.scalar(
        select(Problem).where(
            Problem.text_hash == h, Problem.system_version == version,
            Problem.status.in_(CACHEABLE),
        )
    )  # fmt: skip
    if cached is not None:
        return {"problem_id": str(cached.id)}
    pending = session.scalar(
        select(Job).where(
            Job.kind == "solve", Job.status.in_(("queued", "running")),
            Job.payload["text_hash"].astext == h, Job.payload["system_version"].astext == version,
        )
    )  # fmt: skip
    if pending is not None:
        return {"job_id": str(pending.id)}
    job = Job(
        kind="solve", payload={"text": normalize(text), "text_hash": h, "system_version": version}
    )
    session.add(job)
    session.commit()
    return {"job_id": str(job.id)}


def handle_solve(session: Session, job: Job, ai: AIClient | None = None,
                 sandbox: SandboxClient | None = None) -> None:  # fmt: skip
    payload = dict(job.payload)
    text = payload.pop("text", None)
    job.payload = payload  # the text leaves the database before any work starts
    session.commit()
    if not text:
        raise ValueError("the problem text is no longer available; please submit it again")

    settings = get_settings()
    ai = ai or client_from_settings()
    own_sandbox = sandbox is None
    sandbox = sandbox or SandboxClient()
    budget = Budget(settings.max_tokens_per_problem)
    run = Run(status="running")
    session.add(run)
    session.commit()

    def progress(stage: str, done: int = 0, total: int = 0) -> None:
        job.stage, job.tests_passed, job.tests_total = stage[:64], done, total
        session.commit()

    try:
        result = solve(text, ai, sandbox, budget, progress, settings.max_repair_rounds)
    except Exception as exc:  # our machinery failed: record it, never store a verdict
        session.rollback()
        run.status, run.finished_at = "error", datetime.now(UTC)
        run.failure_reasons, run.tokens = [f"{type(exc).__name__}: {exc}"[:2000]], budget.report()
        session.commit()
        raise
    finally:
        del text
        if own_sandbox:
            sandbox.close()

    problem = store(session, payload["text_hash"], payload["system_version"], result)
    run.problem_id, run.status = problem.id, result.status
    run.stage_timings, run.tokens, run.failure_reasons = (
        result.timings,
        result.tokens,
        result.failures,
    )
    run.finished_at = datetime.now(UTC)
    job.payload = {**payload, "problem_id": str(problem.id)}
    job.stage = "finished"
    session.commit()


def store(session: Session, h: str, version: str, result: SolveResult) -> Problem:
    session.execute(
        delete(Problem).where(Problem.text_hash == h, Problem.system_version == version)
    )
    problem = Problem(
        id=uuid.uuid4(), text_hash=h, system_version=version, status=result.status,
        spec=result.spec, rejection_reason=result.reason or None,
    )  # fmt: skip
    session.add(problem)
    session.flush()
    for i, a in enumerate(result.approaches):
        session.add(Approach(
            problem_id=problem.id, position=i, name=a.name, key_idea=a.key_idea,
            time_complexity=a.time[:64], space_complexity=a.space[:64],
            python_code=a.python_code, cpp_code=a.cpp_code, status=a.status,
            verification={
                "is_brute": a.is_brute, "reason": a.reason, "tests_passed": a.tests_passed,
                "tests_total": a.tests_total, "examples_checked": a.examples_checked,
                "repairs": a.repairs, "failing_case": a.failing_case,
            },
        ))  # fmt: skip
    return problem


def problem_view(session: Session, problem_id: uuid.UUID) -> dict | None:
    problem = session.get(Problem, problem_id)
    if problem is None:
        return None
    approaches = session.scalars(
        select(Approach).where(Approach.problem_id == problem.id).order_by(Approach.position)
    ).all()
    spec = problem.spec or {}
    return {
        "id": str(problem.id),
        "status": problem.status,
        "reason": problem.rejection_reason or "",
        "title": spec.get("title", ""),
        "function_name": spec.get("function_name", ""),
        "params": spec.get("params", []),
        "examples": spec.get("examples", []),
        "comparator": (spec.get("comparator") or {}).get("kind", "exact"),
        "approaches": [
            {
                "id": str(a.id), "name": a.name, "key_idea": a.key_idea,
                "time": a.time_complexity, "space": a.space_complexity,
                "python_code": a.python_code, "cpp_code": a.cpp_code, "status": a.status,
                **{k: v for k, v in (a.verification or {}).items()},
            }
            for a in approaches
        ],
    }  # fmt: skip
