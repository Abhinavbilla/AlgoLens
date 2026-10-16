"""Optional sign-in with Google (OpenID Connect, authorization code flow with PKCE).

Nothing on the site needs an account. Signing in only lets progress follow a learner across
devices, lists the problems they've opened, and raises the tutor's limits.

Flow:
1. /api/auth/google/login makes a random state, nonce and PKCE verifier, keeps them in a
   short-lived HttpOnly cookie, and redirects to Google.
2. Google redirects back to /api/auth/google/callback with a code. The state must match the
   cookie (so nobody can complete a sign-in someone else started), the code is exchanged with
   Google's token endpoint over TLS (with the client secret and the PKCE verifier), and the ID
   token's issuer, audience, expiry and nonce are checked. Because the token comes straight
   from Google's endpoint over TLS rather than through the browser, its signature needn't be
   checked separately (OpenID Connect Core §3.1.3.7).
3. A random session token goes in an HttpOnly, SameSite=Lax cookie; only its SHA-256 is stored.

Only the scopes openid, email and profile are asked for: no access to Gmail, Drive or contacts.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from algolens.db.models import EmailCode, Session, User

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
SESSION_COOKIE = "algolens_session"
FLOW_COOKIE = "algolens_signin"
FLOW_SECONDS = 600  # a sign-in has 10 minutes to come back from Google


class SignInError(Exception):
    """The sign-in can't be completed (the message is safe to show)."""


@dataclass(frozen=True)
class GoogleConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


def google_config(public_url: str) -> GoogleConfig | None:
    """None when Google sign-in isn't set up on this server (the site works without it)."""
    cid, secret = os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        return None
    return GoogleConfig(cid, secret, public_url.rstrip("/") + "/api/auth/google/callback")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def safe_next(path: str | None) -> str:
    """Where to go after signing in: only a path on this site, never another site."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path[:500]


# --- starting and finishing a sign-in ------------------------------------------------------


@dataclass(frozen=True)
class Flow:
    state: str
    nonce: str
    verifier: str
    next: str

    def cookie(self) -> str:
        return ".".join((self.state, self.nonce, self.verifier, _b64url(self.next.encode())))

    @classmethod
    def from_cookie(cls, value: str | None) -> "Flow | None":
        parts = (value or "").split(".")
        if len(parts) != 4:
            return None
        try:
            nxt = base64.urlsafe_b64decode(parts[3] + "=" * (-len(parts[3]) % 4)).decode()
        except ValueError:
            return None
        return cls(parts[0], parts[1], parts[2], safe_next(nxt))


def start(cfg: GoogleConfig, next_path: str | None) -> tuple[str, Flow]:
    """The Google URL to send the browser to, and what to remember in the flow cookie."""
    flow = Flow(secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48),
                safe_next(next_path))  # fmt: skip
    challenge = _b64url(hashlib.sha256(flow.verifier.encode()).digest())
    query = urlencode({
        "client_id": cfg.client_id, "redirect_uri": cfg.redirect_uri, "response_type": "code",
        "scope": "openid email profile", "state": flow.state, "nonce": flow.nonce,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "prompt": "select_account",
    })  # fmt: skip
    return f"{AUTHORIZE_URL}?{query}", flow


def exchange_code(cfg: GoogleConfig, code: str, verifier: str) -> dict:
    """The token endpoint's reply for this code (replaced by a fake in tests)."""
    try:
        r = httpx.post(TOKEN_URL, timeout=15, data={
            "code": code, "client_id": cfg.client_id, "client_secret": cfg.client_secret,
            "redirect_uri": cfg.redirect_uri, "grant_type": "authorization_code",
            "code_verifier": verifier,
        })  # fmt: skip
    except httpx.HTTPError as exc:
        raise SignInError("Couldn't reach Google. Try signing in again.") from exc
    if r.status_code != 200:
        raise SignInError("Google didn't accept this sign-in. Try again.")
    return r.json()


def claims_from(token_reply: dict, cfg: GoogleConfig, nonce: str, now: float | None = None) -> dict:
    """The ID token's claims, after checking it's for us, from Google, current and ours."""
    token = token_reply.get("id_token")
    if not isinstance(token, str) or token.count(".") != 2:
        raise SignInError("Google's reply had no identity in it.")
    payload = token.split(".")[1]
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError as exc:
        raise SignInError("Google's reply couldn't be read.") from exc
    now = time.time() if now is None else now
    aud = claims.get("aud")
    checks = [
        claims.get("iss") in ISSUERS,
        aud == cfg.client_id or (isinstance(aud, list) and cfg.client_id in aud),
        isinstance(claims.get("exp"), int | float) and claims["exp"] > now - 60,
        isinstance(nonce, str) and secrets.compare_digest(str(claims.get("nonce", "")), nonce),
        isinstance(claims.get("sub"), str) and bool(claims["sub"]),
    ]
    if not all(checks):
        raise SignInError("This sign-in couldn't be verified. Try again.")
    if claims.get("email_verified") is not True or not claims.get("email"):
        raise SignInError("Your Google account's email address isn't verified.")
    return claims


# --- users and sessions ---------------------------------------------------------------------


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def upsert_user(db: DbSession, claims: dict) -> User:
    """The account for a Google sign-in. Found by Google id, or else by the same (verified)
    email address, so someone who first signed in by email keeps one account."""
    email = normalize_email(str(claims["email"]))
    user = db.scalar(select(User).where(User.google_sub == claims["sub"]))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(id=uuid.uuid4(), email=email, name="", picture="")
            db.add(user)
        user.google_sub = claims["sub"]
    elif user.email != email and db.scalar(select(User.id).where(User.email == email)) is None:
        user.email = email  # their Google address changed (and no other account has it)
    user.name = str(claims.get("name") or user.name or email.split("@")[0])[:200]
    pic = str(claims.get("picture") or "")
    if pic.startswith("https://"):
        user.picture = pic
    user.last_seen_at = datetime.now(UTC)
    db.flush()
    return user


# --- signing in with an emailed code --------------------------------------------------------

CODE_MINUTES = 10
CODE_ATTEMPTS = 5  # wrong guesses allowed for one code
CODES_PER_HOUR = 5  # codes sent to one address
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def normalize_email(email: str) -> str:
    return email.strip().lower()[:320]


def valid_email(email: str) -> bool:
    return bool(_EMAIL.match(email)) and len(email) <= 254


def _code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


def issue_code(db: DbSession, email: str) -> str | None:
    """A new 6-digit code for the address (replacing any earlier one), or None if it has
    been sent too many codes in the last hour."""
    now = datetime.now(UTC)
    db.execute(delete(EmailCode).where(EmailCode.created_at < now - timedelta(hours=1)))
    recent = db.scalars(select(EmailCode).where(EmailCode.email == email)).all()
    if len(recent) >= CODES_PER_HOUR:
        return None
    for old in recent:  # only the newest code works
        old.expires_at = now
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(EmailCode(email=email, code_hash=_code_hash(email, code),
                     expires_at=now + timedelta(minutes=CODE_MINUTES)))  # fmt: skip
    return code


def check_code(db: DbSession, email: str, code: str) -> bool:
    """True once for the right, unexpired code; each wrong guess counts against it."""
    now = datetime.now(UTC)
    row = db.scalar(
        select(EmailCode)
        .where(EmailCode.email == email, EmailCode.expires_at > now)
        .order_by(EmailCode.created_at.desc())
        .limit(1)
    )
    if row is None or row.attempts >= CODE_ATTEMPTS:
        return False
    code = re.sub(r"\D", "", code)
    if secrets.compare_digest(row.code_hash, _code_hash(email, code)):
        row.expires_at = now  # used up
        return True
    row.attempts += 1
    return False


def email_user(db: DbSession, email: str, name: str = "") -> tuple[User, bool]:
    """The account for this (verified) address, and whether it was just created. A name given
    when signing up replaces the placeholder taken from the address, never a real one."""
    placeholder = email.split("@")[0][:200]
    name = " ".join(name.split())[:80]
    user = db.scalar(select(User).where(User.email == email))
    created = user is None
    if user is None:
        user = User(id=uuid.uuid4(), email=email, name=name or placeholder, picture="")
        db.add(user)
    elif name and user.name == placeholder:
        user.name = name
    user.last_seen_at = datetime.now(UTC)
    db.flush()
    return user, created


def new_session(db: DbSession, user: User, days: int) -> str:
    """A fresh session for the user; returns the token for the cookie (stored only hashed)."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    db.execute(delete(Session).where(Session.user_id == user.id, Session.expires_at < now))
    db.add(Session(token_hash=_hash(token), user_id=user.id, expires_at=now + timedelta(days=days)))
    return token


def user_for(db: DbSession, token: str | None) -> User | None:
    if not token or len(token) > 100:
        return None
    s = db.scalar(select(Session).where(Session.token_hash == _hash(token)))
    if s is None or s.expires_at <= datetime.now(UTC):
        return None
    return db.get(User, s.user_id)


def end_session(db: DbSession, token: str | None) -> None:
    if token:
        db.execute(delete(Session).where(Session.token_hash == _hash(token)))
