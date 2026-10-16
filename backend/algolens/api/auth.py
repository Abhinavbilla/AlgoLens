"""Optional Google sign-in and what a signed-in learner keeps (algolens/auth.py)."""

import logging
import secrets
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from algolens import auth, mailer
from algolens.config import get_settings
from algolens.db.models import Problem, User, UserProblem, UserProgress
from algolens.db.session import session_factory
from algolens.tutor import RateLimit

router = APIRouter(prefix="/api", tags=["accounts"])
log = logging.getLogger("algolens.auth")
CSRF_HEADER = "x-requested-with"  # a custom header: cross-site pages can't send it to us
WRONG_CODE = (
    "That code isn't right, or it has expired. Check the newest email, or ask for a new code."
)
code_limit = RateLimit(per_minute=3, per_day=30)  # codes asked for, per visitor address


def _secure() -> bool:
    return get_settings().public_url.startswith("https://")


def current_user(request: Request) -> User | None:
    """The signed-in user, or None (everything works without one)."""
    token = request.cookies.get(auth.SESSION_COOKIE)
    if not token:
        return None
    with session_factory()() as db:
        user = auth.user_for(db, token)
        if user is not None:
            db.expunge(user)
        return user


def _same_site(request: Request) -> None:
    if request.headers.get(CSRF_HEADER) != "algolens":
        raise HTTPException(403, detail="Missing the X-Requested-With: algolens header.")


def _signed_in(request: Request) -> User:
    user = current_user(request)
    if user is None:
        raise HTTPException(401, detail="Sign in to use this.")
    return user


def _view(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": str(user.id), "email": user.email, "name": user.name, "picture": user.picture}


@router.get("/auth/me")
def me(request: Request) -> dict:
    s = get_settings()
    google = auth.google_config(s.public_url) is not None
    email = mailer.configured(s)
    return {"enabled": google or email, "google": google, "email": email,
            "user": _view(current_user(request))}  # fmt: skip


def _start_session(response: Response, user_id: uuid.UUID) -> None:
    settings = get_settings()
    with session_factory()() as db:
        user = db.get(User, user_id)
        token = auth.new_session(db, user, settings.session_days)
        db.commit()
    response.set_cookie(auth.SESSION_COOKIE, token, max_age=settings.session_days * 86400,
                        httponly=True, secure=_secure(), samesite="lax", path="/")  # fmt: skip


# --- signing in with an emailed code ----------------------------------------------------------


class EmailStart(BaseModel):
    email: str = Field(max_length=320)


class EmailVerify(BaseModel):
    email: str = Field(max_length=320)
    code: str = Field(max_length=20)
    name: str = Field(default="", max_length=80)  # given when signing up


@router.post("/auth/email/start", dependencies=[Depends(_same_site)])
def email_start(body: EmailStart, request: Request) -> dict:
    s = get_settings()
    if not mailer.configured(s):
        raise HTTPException(503, detail="Signing in by email isn't set up on this server.")
    email = auth.normalize_email(body.email)
    if not auth.valid_email(email):
        raise HTTPException(422, detail="That doesn't look like an email address.")
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
    if code_limit.wait_seconds(ip):
        raise HTTPException(429, detail="Too many codes asked for. Wait a minute and try again.")
    with session_factory()() as db:
        code = auth.issue_code(db, email)
        db.commit()
    if code is None:
        raise HTTPException(429, detail="We've sent several codes to this address already. "
                                        "Use the newest one, or try again in an hour.")  # fmt: skip
    try:
        mailer.send_code(s, email, code, auth.CODE_MINUTES)
    except mailer.MailError as exc:
        raise HTTPException(503, detail="We couldn't send the email just now. Try again, "
                                        "or sign in with Google.") from exc  # fmt: skip
    # dev: the code went to the server log, not to an inbox (so the page can say so).
    return {"sent": True, "minutes": auth.CODE_MINUTES, "dev": not mailer.sends_mail(s)}


@router.post("/auth/email/verify", dependencies=[Depends(_same_site)])
def email_verify(body: EmailVerify, response: Response) -> dict:
    email = auth.normalize_email(body.email)
    with session_factory()() as db:
        ok = auth.check_code(db, email, body.code)
        user, created = auth.email_user(db, email, body.name) if ok else (None, False)
        db.commit()
        user_id = user.id if user else None
    if user_id is None:
        raise HTTPException(401, detail=WRONG_CODE)
    _start_session(response, user_id)
    with session_factory()() as db:
        return {"user": _view(db.get(User, user_id)), "created": created}


# --- signing in and out ---------------------------------------------------------------------


@router.get("/auth/google/login")
def google_login(next: str = "/") -> RedirectResponse:
    cfg = auth.google_config(get_settings().public_url)
    if cfg is None:
        raise HTTPException(503, detail="Google sign-in isn't set up on this server.")
    url, flow = auth.start(cfg, next)
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(auth.FLOW_COOKIE, flow.cookie(), max_age=auth.FLOW_SECONDS, httponly=True,
                    secure=_secure(), samesite="lax", path="/api/auth/google")  # fmt: skip
    return resp


def _failed(message: str) -> RedirectResponse:
    resp = RedirectResponse(f"/account?error={quote(message)}", status_code=302)
    resp.delete_cookie(auth.FLOW_COOKIE, path="/api/auth/google")
    return resp


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "",
                    error: str = "") -> RedirectResponse:  # fmt: skip
    settings = get_settings()
    cfg = auth.google_config(settings.public_url)
    flow = auth.Flow.from_cookie(request.cookies.get(auth.FLOW_COOKIE))
    if cfg is None:
        return _failed("Google sign-in isn't set up on this server.")
    if error:
        return _failed("Sign-in was cancelled." if error == "access_denied" else "Sign-in failed.")
    if flow is None or not state or not secrets.compare_digest(state, flow.state):
        return _failed("This sign-in link expired or wasn't started here. Try again.")
    if not code:
        return _failed("Sign-in failed.")
    try:
        claims = auth.claims_from(auth.exchange_code(cfg, code, flow.verifier), cfg, flow.nonce)
    except auth.SignInError as exc:
        log.info("sign-in refused: %s", exc)
        return _failed(str(exc))
    with session_factory()() as db:
        user = auth.upsert_user(db, claims)
        token = auth.new_session(db, user, settings.session_days)
        db.commit()
    resp = RedirectResponse(flow.next, status_code=302)
    resp.delete_cookie(auth.FLOW_COOKIE, path="/api/auth/google")
    resp.set_cookie(auth.SESSION_COOKIE, token, max_age=settings.session_days * 86400,
                    httponly=True, secure=_secure(), samesite="lax", path="/")  # fmt: skip
    return resp


@router.post("/auth/logout", dependencies=[Depends(_same_site)])
def logout(request: Request, response: Response) -> dict:
    with session_factory()() as db:
        auth.end_session(db, request.cookies.get(auth.SESSION_COOKIE))
        db.commit()
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"user": None}


@router.delete("/auth/me", dependencies=[Depends(_same_site)])
def delete_account(request: Request, response: Response) -> dict:
    """Deletes the account and everything kept for it (sessions, progress, problem list)."""
    user = _signed_in(request)
    with session_factory()() as db:
        db.execute(delete(User).where(User.id == user.id))
        db.commit()
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"deleted": True}


# --- what a signed-in learner keeps ------------------------------------------------------------


class Progress(BaseModel):
    done: list[str] = Field(max_length=2000)


def _clean(done: list[str]) -> list[str]:
    return sorted({d for d in done if 0 < len(d) <= 100})


@router.get("/me/progress")
def get_progress(request: Request) -> dict:
    user = _signed_in(request)
    with session_factory()() as db:
        row = db.get(UserProgress, user.id)
        return {"done": list(row.done) if row else []}


@router.put("/me/progress", dependencies=[Depends(_same_site)])
def put_progress(body: Progress, request: Request) -> dict:
    """Replaces the stored list (the browser merges its own list in before sending)."""
    user = _signed_in(request)
    done = _clean(body.done)
    with session_factory()() as db:
        row = db.get(UserProgress, user.id)
        if row is None:
            db.add(UserProgress(user_id=user.id, done=done))
        else:
            row.done = done
        db.commit()
    return {"done": done}


@router.get("/me/problems")
def my_problems(request: Request) -> list[dict]:
    user = _signed_in(request)
    with session_factory()() as db:
        rows = db.execute(
            select(Problem, UserProblem.added_at)
            .join(UserProblem, UserProblem.problem_id == Problem.id)
            .where(UserProblem.user_id == user.id)
            .order_by(UserProblem.added_at.desc())
            .limit(200)
        ).all()
    return [
        {"id": str(p.id), "title": (p.spec or {}).get("title") or (p.spec or {}).get(
            "function_name") or "Untitled problem", "status": p.status,
         "added_at": added.isoformat()}
        for p, added in rows
    ]  # fmt: skip


@router.post("/me/problems/{problem_id}", dependencies=[Depends(_same_site)])
def remember_problem(problem_id: uuid.UUID, request: Request) -> dict:
    user = _signed_in(request)
    with session_factory()() as db:
        if db.get(Problem, problem_id) is None:
            raise HTTPException(404, detail="no such problem")
        if db.get(UserProblem, (user.id, problem_id)) is None:
            db.add(UserProblem(user_id=user.id, problem_id=problem_id))
            db.commit()
    return {"saved": True}


@router.delete("/me/problems/{problem_id}", dependencies=[Depends(_same_site)])
def forget_problem(problem_id: uuid.UUID, request: Request) -> dict:
    user = _signed_in(request)
    with session_factory()() as db:
        db.execute(delete(UserProblem).where(UserProblem.user_id == user.id,
                                             UserProblem.problem_id == problem_id))  # fmt: skip
        db.commit()
    return {"saved": False}
