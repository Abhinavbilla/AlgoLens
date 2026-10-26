"""The tutor chat and "check my code" (algolens/tutor.py)."""

import hashlib
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from algolens.ai.budget import Budget, BudgetExhausted
from algolens.ai.client import (
    AIError,
    AIUnavailable,
    QuotaExhausted,
    client_from_settings,
    parse_role,
)
from algolens.api.auth import current_user
from algolens.api.library import UNAVAILABLE, _row, _verification
from algolens.api.problems import NO_PROBLEM
from algolens.db.models import Approach, Problem
from algolens.db.session import session_factory
from algolens.library.loader import from_row
from algolens.pipeline.service import KEY_ENV, input_rules, problem_view
from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.describe import describe
from algolens.schema.model import compile_schema
from algolens.tutor import (
    MAX_REPLY_TOKENS,
    ChatRequest,
    CheckRequest,
    Context,
    NotCheckable,
    RateLimit,
    check_code,
    library_context,
    library_target,
    problem_context,
    problem_target,
    system_prompt,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger("algolens.chat")
limit = RateLimit()
signed_in_limit = RateLimit(per_minute=20, per_day=400)  # per account, not per address
CHAT_BUDGET = 40_000  # tokens for one reply (the context plus the conversation plus the answer)


def _visitor(request: Request) -> str:
    # nginx sets X-Real-IP; without it (tests, direct access) use the connection's address.
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "?")


def _throttle(request: Request) -> None:
    user = current_user(request)
    if user is not None:
        wait = signed_in_limit.wait_seconds(f"user:{user.id}")
    else:
        wait = limit.wait_seconds(_visitor(request))
    if wait:
        when = f"{wait} seconds" if wait < 120 else f"{round(wait / 60)} minutes"
        raise HTTPException(429, detail=f"That's a lot of questions at once. Try again in {when}.")


def _seed(ctx: Context) -> int:
    return int(hashlib.sha256(f"{ctx.kind}:{ctx.id}".encode()).hexdigest()[:8], 16)


def _problem(ctx: Context) -> tuple[Problem, list[Approach]]:
    try:
        pid = uuid.UUID(ctx.id)
    except ValueError:
        raise HTTPException(404, detail=NO_PROBLEM) from None
    with session_factory()() as session:
        problem = session.get(Problem, pid)
        if problem is None:
            raise HTTPException(404, detail=NO_PROBLEM)
        approaches = session.scalars(
            select(Approach).where(Approach.problem_id == pid).order_by(Approach.position)
        ).all()
    if problem.status != "done":
        raise HTTPException(409, detail="The tutor needs a solved problem to talk about.")
    return problem, list(approaches)


def _context_text(ctx: Context) -> str:
    if ctx.kind == "library":
        row = _row(ctx.id)
        entry = from_row(row)
        schema = compile_schema(entry.schema)
        hints = [{"name": p.name, "hint": describe(p.type)} for p in schema.params]
        return library_context(entry, hints, _verification(row))
    problem, _ = _problem(ctx)
    with session_factory()() as session:
        view = problem_view(session, problem.id)
    return problem_context(view or {}, ctx.approach_id)


@router.post("")
def chat(body: ChatRequest, request: Request) -> dict:
    ai = client_from_settings()
    try:
        provider, _ = parse_role(ai.roles["tutor"])
    except AIUnavailable as exc:
        raise HTTPException(503, detail="The tutor isn't set up on this server.") from exc
    if provider != "fake" and not os.environ.get(KEY_ENV[provider]):
        raise HTTPException(
            503, detail=f"The tutor isn't set up yet (missing {KEY_ENV[provider]})."
        )
    system = system_prompt(body.mode, _context_text(body.context), body.context.step)
    _throttle(request)
    messages = [m.model_dump() for m in body.messages]
    try:
        reply = ai.complete_text("tutor", system, messages, Budget(CHAT_BUDGET), MAX_REPLY_TOKENS)
    except BudgetExhausted as exc:
        raise HTTPException(413, detail="This conversation is too long; start a new one.") from exc
    except QuotaExhausted as exc:
        log.warning("tutor stopped: %s", exc)
        raise HTTPException(503, detail=exc.friendly("The tutor can't answer")) from exc
    except AIError as exc:
        log.warning("tutor call failed: %s", exc)
        raise HTTPException(
            503, detail="The tutor couldn't reach the AI service. Try again in a moment."
        ) from exc
    finally:
        ai.close()
    return {"reply": reply.text}


@router.post("/check")
def check(body: CheckRequest, request: Request) -> dict:
    """Run the learner's code against verified code (no AI involved)."""
    ctx = body.context
    if ctx.kind == "library":
        target = library_target(from_row(_row(ctx.id)), _seed(ctx))
    else:
        problem, approaches = _problem(ctx)
        try:
            target = problem_target(problem.spec or {}, approaches, input_rules(problem.spec),
                                    _seed(ctx))  # fmt: skip
        except NotCheckable as exc:
            raise HTTPException(409, detail=str(exc)) from exc
    _throttle(request)
    client = SandboxClient()
    try:
        return check_code(body.code, target, client)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail=UNAVAILABLE) from exc
    finally:
        client.close()
