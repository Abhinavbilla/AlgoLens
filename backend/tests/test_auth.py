"""Optional Google sign-in, with Google's token endpoint replaced by a fake."""

import base64
import json
import time
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select

from algolens import auth, mailer
from algolens.api import app as app_module
from algolens.api import auth as auth_api
from algolens.config import get_settings
from algolens.db import session as session_module
from algolens.db.models import EmailCode, Problem, Session, User, UserProblem, UserProgress

CLIENT_ID = "test-client.apps.googleusercontent.com"
HEADERS = {"X-Requested-With": "algolens"}


def id_token(**claims) -> str:
    def part(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'RS256'})}.{part(claims)}.signature"


def good_claims(sent_nonce, **over):
    return {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "exp": time.time() + 3600,
            "nonce": sent_nonce, "sub": "google-123", "email": "learner@example.com",
            "email_verified": True, "name": "Ada Learner",
            "picture": "https://lh3.googleusercontent.com/a/x", **over}  # fmt: skip


@pytest.fixture
def factory(db_url, monkeypatch):
    engine = create_engine(db_url)
    monkeypatch.setattr(session_module, "get_engine", lambda url=None: engine)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    get_settings.cache_clear()
    f = session_module.session_factory(engine)
    with f() as s:
        s.execute(delete(User))
        s.execute(delete(Problem))
        s.execute(delete(EmailCode))
        s.commit()
    yield f
    get_settings.cache_clear()
    engine.dispose()


@pytest.fixture
def google(monkeypatch):
    """What the fake token endpoint will say: a function of the nonce Google was sent."""
    reply = {"claims": good_claims, "status": None}

    def exchange(cfg, code, verifier):
        assert cfg.client_secret == "test-secret" and code == "the-code" and len(verifier) >= 43
        if reply["status"]:
            raise auth.SignInError("Google didn't accept this sign-in. Try again.")
        return {"id_token": id_token(**reply["claims"](reply["nonce"]))}

    monkeypatch.setattr(auth, "exchange_code", exchange)
    return reply


def client():
    return TestClient(app_module.create_app(), follow_redirects=False)


def sign_in(c, google, next_path="/path", state=None):
    r = c.get("/api/auth/google/login", params={"next": next_path})
    assert r.status_code == 302
    query = parse_qs(urlparse(r.headers["location"]).query)
    google["nonce"] = query["nonce"][0]
    return c.get("/api/auth/google/callback",
                 params={"code": "the-code", "state": state or query["state"][0]})  # fmt: skip


def test_without_google_configured_everything_else_still_works(factory, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    c = client()
    assert c.get("/api/auth/me").json() == {
        "enabled": False,
        "google": False,
        "email": False,
        "user": None,
    }
    assert c.get("/api/auth/google/login").status_code == 503
    assert c.get("/api/library").status_code == 200


def test_sign_in_round_trip(factory, google):
    c = client()
    r = c.get("/api/auth/google/login", params={"next": "/library/kadane"})
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert q["client_id"] == [CLIENT_ID] and q["scope"] == ["openid email profile"]
    assert q["code_challenge_method"] == ["S256"] and q["redirect_uri"] == [
        "http://localhost:8080/api/auth/google/callback"
    ]
    assert "httponly" in r.headers["set-cookie"].lower()

    r = sign_in(c, google, "/library/kadane")
    assert r.status_code == 302 and r.headers["location"] == "/library/kadane"
    cookie = r.headers["set-cookie"].lower()
    assert "algolens_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    me = c.get("/api/auth/me").json()
    assert me["enabled"] and me["user"]["email"] == "learner@example.com"
    assert me["user"]["name"] == "Ada Learner"
    with factory() as s:  # only a hash of the token is stored
        token = c.cookies.get(auth.SESSION_COOKIE)
        stored = s.scalars(select(Session.token_hash)).all()
        assert len(stored) == 1 and token not in stored[0]
    # Signing in again finds the same user rather than making another.
    sign_in(c, google)
    with factory() as s:
        assert len(s.scalars(select(User)).all()) == 1


@pytest.mark.parametrize("bad", [
    {"aud": "someone-else.apps.googleusercontent.com"},
    {"iss": "https://evil.example.com"},
    {"exp": time.time() - 3600},
    {"nonce": "replayed"},
    {"email_verified": False},
    {"sub": ""},
])  # fmt: skip
def test_tokens_that_dont_check_out_are_refused(factory, google, bad):
    google["claims"] = lambda nonce: good_claims(nonce, **bad)
    c = client()
    r = sign_in(c, google)
    assert r.status_code == 302 and r.headers["location"].startswith("/account?error=")
    assert c.get("/api/auth/me").json()["user"] is None


def test_a_sign_in_started_elsewhere_is_refused(factory, google):
    c = client()
    r = sign_in(c, google, state="attacker-chosen-state")
    assert r.headers["location"].startswith("/account?error=")
    assert c.get("/api/auth/me").json()["user"] is None
    # No flow cookie at all (the callback opened in another browser).
    fresh = client()
    r = fresh.get("/api/auth/google/callback", params={"code": "the-code", "state": "x"})
    assert r.headers["location"].startswith("/account?error=")


def test_google_refusing_or_cancelling(factory, google):
    google["status"] = 400
    assert sign_in(client(), google).headers["location"].startswith("/account?error=")
    r = client().get("/api/auth/google/callback", params={"error": "access_denied"})
    assert "cancelled" in r.headers["location"]


def test_next_never_leaves_the_site():
    for bad in ("//evil.com", "https://evil.com", "/\\evil.com", "", None, "evil"):
        assert auth.safe_next(bad) == "/"
    assert auth.safe_next("/problems/abc?x=1") == "/problems/abc?x=1"


def test_changes_need_the_same_site_header(factory, google):
    c = client()
    sign_in(c, google)
    assert c.post("/api/auth/logout").status_code == 403
    assert c.put("/api/me/progress", json={"done": ["kadane"]}).status_code == 403
    assert c.delete("/api/auth/me").status_code == 403
    assert c.get("/api/auth/me").json()["user"] is not None  # still signed in


def test_logout(factory, google):
    c = client()
    sign_in(c, google)
    token = c.cookies.get(auth.SESSION_COOKIE)
    assert c.post("/api/auth/logout", headers=HEADERS).status_code == 200
    assert c.get("/api/auth/me").json()["user"] is None
    # The old token is dead even if someone kept a copy of it.
    other = client()
    other.cookies.set(auth.SESSION_COOKIE, token)
    assert other.get("/api/auth/me").json()["user"] is None


def test_progress_sync(factory, google):
    c = client()
    assert c.get("/api/me/progress").status_code == 401
    sign_in(c, google)
    assert c.get("/api/me/progress").json() == {"done": []}
    r = c.put("/api/me/progress", headers=HEADERS,
              json={"done": ["kadane", "primer:arrays", "kadane", ""]})  # fmt: skip
    assert r.json() == {"done": ["kadane", "primer:arrays"]}
    assert c.get("/api/me/progress").json() == {"done": ["kadane", "primer:arrays"]}


def test_my_problems_are_private(factory, google):
    with factory() as s:
        p = Problem(id=uuid.uuid4(), text_hash="h", system_version="v", status="done",
                    spec={"title": "Two Sum"})  # fmt: skip
        s.add(p)
        s.commit()
        pid = str(p.id)
    a = client()
    sign_in(a, google)
    assert a.post(f"/api/me/problems/{pid}", headers=HEADERS).json() == {"saved": True}
    a.post(f"/api/me/problems/{pid}", headers=HEADERS)  # twice is fine
    assert [x["title"] for x in a.get("/api/me/problems").json()] == ["Two Sum"]
    assert a.post(f"/api/me/problems/{uuid.uuid4()}", headers=HEADERS).status_code == 404

    google["claims"] = lambda nonce: good_claims(nonce, sub="google-456", email="b@example.com")
    b = client()
    sign_in(b, google)
    assert b.get("/api/me/problems").json() == []
    a.delete(f"/api/me/problems/{pid}", headers=HEADERS)
    assert a.get("/api/me/problems").json() == []


def test_delete_account_removes_everything(factory, google):
    with factory() as s:
        p = Problem(id=uuid.uuid4(), text_hash="h2", system_version="v", status="done", spec={})
        s.add(p)
        s.commit()
        pid = p.id
    c = client()
    sign_in(c, google)
    c.put("/api/me/progress", headers=HEADERS, json={"done": ["kadane"]})
    c.post(f"/api/me/problems/{pid}", headers=HEADERS)
    assert c.delete("/api/auth/me", headers=HEADERS).json() == {"deleted": True}
    assert c.get("/api/auth/me").json()["user"] is None
    with factory() as s:
        for table in (User, Session, UserProgress, UserProblem):
            assert s.scalars(select(table)).all() == []
        assert s.get(Problem, pid) is not None  # the shared problem itself stays


# --- signing in with an emailed code ----------------------------------------------------------


@pytest.fixture
def inbox(factory, monkeypatch):
    """Email sign-in switched on, with codes delivered here instead of sent."""
    monkeypatch.setenv("ALGOLENS_EMAIL_DEV_LOG", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth_api, "code_limit", auth_api.RateLimit(per_minute=100, per_day=1000))
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        mailer, "send_code", lambda s, to, code, minutes: sent.__setitem__(to, code)
    )
    return sent


def ask_code(c, email):
    return c.post("/api/auth/email/start", headers=HEADERS, json={"email": email})


def verify(c, email, code):
    return c.post("/api/auth/email/verify", headers=HEADERS, json={"email": email, "code": code})


def test_email_sign_in(inbox):
    c = client()
    assert c.get("/api/auth/me").json()["email"] is True
    assert ask_code(c, "  Ada@Example.com ").json() == {"sent": True, "minutes": 10, "dev": True}
    code = inbox["ada@example.com"]
    assert len(code) == 6 and code.isdigit()
    r = verify(c, "ada@example.com", code[:3] + " " + code[3:])  # spaces are fine
    assert r.status_code == 200 and r.json()["user"]["email"] == "ada@example.com"
    assert "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/auth/me").json()["user"]["name"] == "ada"
    assert verify(client(), "ada@example.com", code).status_code == 401  # works only once


def test_wrong_codes_lock_the_code(inbox):
    c = client()
    ask_code(c, "ada@example.com")
    code = inbox["ada@example.com"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert verify(c, "ada@example.com", wrong).status_code == 401
    assert verify(c, "ada@example.com", code).status_code == 401  # too many guesses
    assert c.get("/api/auth/me").json()["user"] is None


def test_only_the_newest_code_works_and_codes_expire(inbox, factory):
    c = client()
    ask_code(c, "ada@example.com")
    first = inbox["ada@example.com"]
    ask_code(c, "ada@example.com")
    second = inbox["ada@example.com"]
    if first != second:
        assert verify(c, "ada@example.com", first).status_code == 401
    with factory() as s:
        for row in s.scalars(select(EmailCode)).all():
            row.expires_at = row.created_at  # ten minutes have passed
        s.commit()
    assert verify(c, "ada@example.com", second).status_code == 401


def test_code_requests_are_limited(inbox, monkeypatch):
    c = client()
    for _ in range(5):
        assert ask_code(c, "ada@example.com").status_code == 200
    assert ask_code(c, "ada@example.com").status_code == 429  # per address, per hour
    monkeypatch.setattr(auth_api, "code_limit", auth_api.RateLimit(per_minute=1, per_day=10))
    assert ask_code(c, "b@example.com").status_code == 200
    assert ask_code(c, "c@example.com").status_code == 429  # per visitor


def test_email_requests_are_checked(inbox):
    c = client()
    assert ask_code(c, "not-an-email").status_code == 422
    assert c.post("/api/auth/email/start", json={"email": "a@example.com"}).status_code == 403
    assert inbox == {}


def test_email_sign_in_off_without_mail_settings(factory):
    c = client()
    assert c.get("/api/auth/me").json()["email"] is False
    assert ask_code(c, "ada@example.com").status_code == 503


def test_email_then_google_is_one_account(inbox, google, factory):
    c = client()
    ask_code(c, "learner@example.com")
    verify(c, "learner@example.com", inbox["learner@example.com"])
    c.put("/api/me/progress", headers=HEADERS, json={"done": ["kadane"]})
    g = client()
    sign_in(g, google)  # Google says learner@example.com, verified
    assert g.get("/api/me/progress").json() == {"done": ["kadane"]}
    with factory() as s:
        users = s.scalars(select(User)).all()
        assert len(users) == 1 and users[0].google_sub == "google-123"


def test_google_then_email_is_one_account(inbox, google, factory):
    g = client()
    sign_in(g, google)
    c = client()
    ask_code(c, "LEARNER@example.com")
    verify(c, "learner@example.com", inbox["learner@example.com"])
    assert c.get("/api/auth/me").json()["user"]["name"] == "Ada Learner"
    with factory() as s:
        assert len(s.scalars(select(User)).all()) == 1


def test_sign_up_with_a_name(inbox):
    c = client()
    ask_code(c, "grace@example.com")
    r = c.post("/api/auth/email/verify", headers=HEADERS,
               json={"email": "grace@example.com", "code": inbox["grace@example.com"],
                     "name": "  Grace   Hopper "})  # fmt: skip
    assert r.json()["created"] is True and r.json()["user"]["name"] == "Grace Hopper"
    # Logging in later (no name, or a different one) keeps the name they chose.
    ask_code(c, "grace@example.com")
    r = c.post("/api/auth/email/verify", headers=HEADERS,
               json={"email": "grace@example.com", "code": inbox["grace@example.com"],
                     "name": "Someone Else"})  # fmt: skip
    assert r.json()["created"] is False and r.json()["user"]["name"] == "Grace Hopper"


def test_a_name_replaces_only_the_placeholder(inbox):
    c = client()
    ask_code(c, "lin@example.com")
    verify(c, "lin@example.com", inbox["lin@example.com"])  # logged in without a name
    assert c.get("/api/auth/me").json()["user"]["name"] == "lin"
    ask_code(c, "lin@example.com")
    r = c.post(
        "/api/auth/email/verify",
        headers=HEADERS,
        json={"email": "lin@example.com", "code": inbox["lin@example.com"], "name": "Lin Wu"},
    )
    assert r.json()["user"]["name"] == "Lin Wu"
