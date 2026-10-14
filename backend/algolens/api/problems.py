"""Pasted problems: submit, follow the job, read the result (plan §7)."""

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from algolens.db.models import Job
from algolens.db.session import session_factory
from algolens.pipeline.service import MAX_TEXT, missing_keys, normalize, problem_view, submit

router = APIRouter(prefix="/api", tags=["problems"])
FINAL = ("done", "failed")


class Submission(BaseModel):
    text: str = Field(max_length=MAX_TEXT * 2)  # normalized length is checked below


@router.post("/problems", status_code=202)
def post_problem(body: Submission, response: Response) -> dict:
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
    with session_factory()() as session:
        out = submit(session, text)
    if "problem_id" in out:
        response.status_code = 200
    return out


def _job_view(job: Job) -> dict:
    return {
        "id": str(job.id),
        "status": job.status,
        "stage": job.stage or ("waiting in the queue" if job.status == "queued" else ""),
        "tests_passed": job.tests_passed,
        "tests_total": job.tests_total,
        "error": job.error or "",
        "problem_id": (job.payload or {}).get("problem_id"),
    }


def _load_job(job_id: uuid.UUID) -> dict:
    with session_factory()() as session:
        job = session.scalar(select(Job).where(Job.id == job_id, Job.kind == "solve"))
        if job is None:
            raise HTTPException(404, detail="no such job")
        return _job_view(job)


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
        raise HTTPException(404, detail="no such problem")
    return view
