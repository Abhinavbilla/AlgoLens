"""Pasted problems: submit, follow the job, read the result (plan §7)."""

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from algolens.api.auth import current_user
from algolens.api.library import UNAVAILABLE, _animation_or_error
from algolens.compare import cached_compare
from algolens.config import get_settings
from algolens.db.models import Approach, Job, Problem
from algolens.db.session import session_factory
from algolens.pipeline.allowance import (
    DailyLimitReached,
    allowance,
    queue_position,
    visitor_key,
)
from algolens.pipeline.service import (
    MAX_TEXT,
    input_rules,
    missing_keys,
    normalize,
    problem_view,
    submit,
)
from algolens.pipeline.visualize import AnimationSource, sandbox_extras
from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.service import check_input
from algolens.tutor import RateLimit

router = APIRouter(prefix="/api", tags=["problems"])
FINAL = ("done", "failed")
NO_PROBLEM = (
    "This problem isn't stored anymore (results are cleared when AlgoLens is updated). "
    "Paste it again to solve it."
)


class Submission(BaseModel):
    text: str = Field(max_length=MAX_TEXT * 2)  # normalized length is checked below
    retry: bool = False  # solve again if the cached result isn't fully verified


# "Try again" re-runs the whole pipeline, so it's limited per visitor: free AI tiers allow only
# a few problems a day.
retry_limit = RateLimit(per_minute=1, per_day=10)


def _visitor(request: Request) -> tuple[str, int]:
    """The visitor's key for the daily limit, and their limit."""
    settings = get_settings()
    user = current_user(request)
    if user is not None:
        return visitor_key(str(user.id), ""), settings.problems_per_day_signed_in
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
    return visitor_key(None, ip), settings.problems_per_day


@router.get("/problems/allowance")
def get_allowance(request: Request) -> dict:
    """How many new problems this visitor can still have solved today."""
    visitor, limit = _visitor(request)
    if limit == 0:
        return {"limit": 0, "used": 0, "in_progress": 0, "left": None, "retry_at": None}
    with session_factory()() as session:
        return allowance(session, visitor, limit).view()


@router.post("/problems", status_code=202)
def post_problem(body: Submission, request: Request, response: Response) -> dict:
    text = normalize(body.text)
    if len(text) < 20:
        raise HTTPException(422, detail="Paste the full problem statement, with an example.")
    if len(text) > MAX_TEXT:
        raise HTTPException(422, detail=f"The statement is too long (over {MAX_TEXT} characters).")
    keys = missing_keys()
    if keys:
        raise HTTPException(
            503, detail=f"Solving new problems isn't set up yet (missing {', '.join(keys)}). "
            "The library still works.",
        )  # fmt: skip
    if body.retry:
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
        wait = retry_limit.wait_seconds(ip)
        if wait:
            raise HTTPException(429, detail="You've retried a lot today. Try again in "
                                            f"{round(wait / 60) or 1} minutes.")  # fmt: skip
    visitor, limit = _visitor(request)
    with session_factory()() as session:
        try:
            out = submit(session, text, retry=body.retry, visitor=visitor, daily_limit=limit)
        except DailyLimitReached as exc:
            raise HTTPException(429, detail={
                "message": str(exc), "issues": [], "kind": "daily_limit",
                "allowance": exc.allowance.view(),
            }) from exc  # fmt: skip
    if "problem_id" in out:
        response.status_code = 200
    return out


def _job_view(session: Session, job: Job) -> dict:
    return {
        "id": str(job.id),
        "status": job.status,
        "stage": job.stage or ("waiting in the queue" if job.status == "queued" else ""),
        "tests_passed": job.tests_passed,
        "tests_total": job.tests_total,
        "error": job.error or "",
        "problem_id": (job.payload or {}).get("problem_id"),
        # Why a failed job stopped (see algolens/failures.py), so the page can title it.
        "error_kind": (job.payload or {}).get("error_kind"),
        # Set when the free AI allowance ran out: when it should be back (ISO time or None).
        "quota": (job.payload or {}).get("quota"),
        # Waiting: how many are ahead and roughly how long until it starts.
        "queue": queue_position(session, job),
    }


def _load_job(job_id: uuid.UUID) -> dict:
    with session_factory()() as session:
        job = session.scalar(select(Job).where(Job.id == job_id, Job.kind == "solve"))
        if job is None:
            raise HTTPException(
                404,
                detail="This job wasn't found. It may be from before the "
                "server was reset. Please paste the problem again.",
            )
        return _job_view(session, job)


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID) -> dict:
    return _load_job(job_id)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: uuid.UUID) -> StreamingResponse:
    first = await asyncio.to_thread(_load_job, job_id)  # 404 before the stream starts

    async def stream():
        last, view = None, first
        for tick in range(3600):  # an hour at most; the client reconnects or polls after that
            if view != last:
                yield f"data: {json.dumps(view)}\n\n"
                last = view
            elif tick % 15 == 0:
                yield ": keep-alive\n\n"  # stops proxies closing a quiet stream
            if view["status"] in FINAL:
                return
            await asyncio.sleep(1)
            view = await asyncio.to_thread(_load_job, job_id)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)


@router.get("/problems/{problem_id}")
def get_problem(problem_id: uuid.UUID) -> dict:
    with session_factory()() as session:
        view = problem_view(session, problem_id)
    if view is None:
        raise HTTPException(404, detail=NO_PROBLEM)
    return view


# --- animations of verified approaches ------------------------------------------------------


def _approach_source(problem_id: uuid.UUID, approach_id: uuid.UUID):
    with session_factory()() as session:
        problem = session.get(Problem, problem_id)
        approach = session.get(Approach, approach_id)
        if problem is None or approach is None or approach.problem_id != problem.id:
            raise HTTPException(404, detail="This approach wasn't found. Reload the page.")
    plan = approach.visual_spec or {}
    if not plan or "unavailable" in plan:
        message = plan.get("unavailable") or "Only verified approaches are animated."
        raise HTTPException(409, detail={"message": message, "issues": []})
    spec = problem.spec or {}
    source = AnimationSource(str(approach.id), spec["function_name"], approach.python_code,
                             sandbox_extras(spec), plan, approach.cpp_code)  # fmt: skip
    return spec, source


@router.get("/problems/{problem_id}/approaches/{approach_id}/animation")
def get_approach_animation(problem_id: uuid.UUID, approach_id: uuid.UUID) -> dict:
    _, source = _approach_source(problem_id, approach_id)
    return _animation_or_error(source, source.default_input, custom=False)


class CustomInput(BaseModel):
    args: list


@router.post("/problems/{problem_id}/approaches/{approach_id}/animation")
def post_approach_animation(problem_id: uuid.UUID, approach_id: uuid.UUID,
                            body: CustomInput) -> dict:  # fmt: skip
    """A learner's own input, checked against the problem's input rules before anything runs."""
    spec, source = _approach_source(problem_id, approach_id)
    client = SandboxClient()
    try:
        issues = check_input(input_rules(spec), body.args, client)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail={"message": UNAVAILABLE, "issues": []}) from exc
    finally:
        client.close()
    if issues:
        raise HTTPException(422, detail={
            "message": "This input doesn't fit the problem.",
            "issues": [{"path": i.path, "message": i.message} for i in issues],
        })  # fmt: skip
    return _animation_or_error(source, {"args": body.args}, custom=True)


@router.get("/problems/{problem_id}/compare")
def get_compare(problem_id: uuid.UUID) -> dict:
    """Executed lines vs input size for every verified approach."""
    with session_factory()() as session:
        problem = session.get(Problem, problem_id)
        if problem is None:
            raise HTTPException(404, detail=NO_PROBLEM)
        rows = session.scalars(
            select(Approach)
            .where(Approach.problem_id == problem.id, Approach.status == "verified")
            .order_by(Approach.position)
        ).all()
    if problem.status != "done" or not rows:
        raise HTTPException(409, detail={"message": "No verified approaches to compare.",
                                         "issues": []})  # fmt: skip
    approaches = [{"id": str(a.id), "name": a.name, "python_code": a.python_code} for a in rows]
    key = f"{problem.id}:" + ",".join(a["id"] for a in approaches)
    try:
        return cached_compare(key, problem.spec or {}, approaches)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail={"message": UNAVAILABLE, "issues": []}) from exc
