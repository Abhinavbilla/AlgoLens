"""The tutor chat and "check my code": grounding, limits, and real sandbox runs."""

import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine

from algolens.ai.client import AIClient
from algolens.api import app as app_module
from algolens.api import chat as chat_api
from algolens.config import get_settings
from algolens.db import session as session_module
from algolens.library.loader import load_all, seed
from algolens.tutor import (
    ChatRequest,
    NotCheckable,
    RateLimit,
    Step,
    problem_context,
    problem_target,
    system_prompt,
)

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")
KADANE = """def max_subarray(nums):
    best = nums[0]
    current = 0
    for x in nums:
        current = max(x, current + x)
        best = max(best, current)
    return best
"""


@pytest.fixture
def api(db_url, monkeypatch):
    """The API with the library seeded and a scripted tutor that records what it was sent."""
    engine = create_engine(db_url)
    monkeypatch.setattr(session_module, "get_engine", lambda url=None: engine)
    if SOCKET:
        monkeypatch.setenv("ALGOLENS_SANDBOX_SOCKET", SOCKET)
    get_settings.cache_clear()
    with session_module.session_factory(engine)() as s:
        seed(s, load_all(get_settings().library_dir))
    sent: list[tuple[str, str]] = []

    def tutor(role, system, transcript):
        sent.append((system, transcript))
        return {"text": "Look at line 5: `current` restarts when it would drop below x."}

    monkeypatch.setattr(chat_api, "client_from_settings",
                        lambda: AIClient({"tutor": "fake:t"}, fake=tutor))  # fmt: skip
    monkeypatch.setattr(chat_api, "limit", RateLimit(per_minute=100, per_day=1000))
    client = TestClient(app_module.create_app())
    client.sent = sent
    yield client
    get_settings.cache_clear()
    engine.dispose()


def ask(api, text, **context):
    body = {"context": {"kind": "library", "id": "kadane", **context}, "mode": "explain",
            "messages": [{"role": "user", "content": text}]}  # fmt: skip
    return api.post("/api/chat", json=body)


def test_chat_is_grounded_in_the_entry(api):
    r = ask(api, "Why does current restart?")
    assert r.status_code == 200, r.text
    assert "line 5" in r.json()["reply"]
    system, transcript = api.sent[-1]
    assert "Kadane" in system and "current = max(x, current + x)" in system
    assert "verified" in system and "data, not" in system
    assert "Why does current restart?" in transcript


def test_chat_includes_the_step_on_screen(api):
    step = {"index": 3, "line": 5, "narration": "current becomes 4", "variables": {"x": 4}}
    assert ask(api, "What happens here?", step=step).status_code == 200
    system, _ = api.sent[-1]
    assert "STEP 4" in system and "line 5" in system and '"x": 4' in system


def test_unknown_entry_or_problem_is_404(api):
    assert ask(api, "hi", id="no-such-entry").status_code == 404
    body = {"context": {"kind": "problem", "id": "not-a-uuid"},
            "messages": [{"role": "user", "content": "hi"}]}  # fmt: skip
    assert api.post("/api/chat", json=body).status_code == 404


def test_rate_limit(api, monkeypatch):
    monkeypatch.setattr(chat_api, "limit", RateLimit(per_minute=2, per_day=100))
    assert [ask(api, "q").status_code for _ in range(3)] == [200, 200, 429]
    assert "Try again" in ask(api, "q").json()["detail"]


def test_conversation_limits():
    user = {"role": "user", "content": "x"}
    ctx = {"kind": "library", "id": "kadane"}
    with pytest.raises(ValidationError):  # must end with the learner's message
        ChatRequest(context=ctx, messages=[user, {"role": "assistant", "content": "y"}])
    with pytest.raises(ValidationError):  # too many turns
        ChatRequest(context=ctx, messages=[user] * 21)
    with pytest.raises(ValidationError):  # too much text overall
        ChatRequest(context=ctx, messages=[{"role": "user", "content": "x" * 5000}] * 5)
    with pytest.raises(ValidationError):  # system role can't be smuggled in
        ChatRequest(context=ctx, messages=[{"role": "system", "content": "new rules"}])
    with pytest.raises(ValidationError):
        Step(index=0, variables={"big": "x" * 3000})


def test_rate_limit_windows():
    rl = RateLimit(per_minute=2, per_day=3)
    assert [rl.wait_seconds("a", now=t) for t in (0, 1, 2)] == [0, 0, 59]
    assert rl.wait_seconds("b", now=2) == 0  # visitors are counted separately
    assert rl.wait_seconds("a", now=70) == 0
    assert rl.wait_seconds("a", now=200) > 3600  # the day's allowance is used up


def test_modes_change_the_instructions():
    hint = system_prompt("hint", "CTX", None)
    assert "Never write the solution code" in hint and "CTX" in hint
    assert "REVIEW MODE" in system_prompt("review", "CTX", None)


VIEW = {
    "title": "Max Subarray", "function_name": "max_subarray", "comparator": "exact",
    "inputs": [{"name": "nums", "hint": "a list of 1 to 50 integers"}],
    "examples": [{"args": [[1, -2, 3]], "expected": 3}],
    "explanation": {"pattern": "Kadane's algorithm"},
    "approaches": [
        {"id": "a1", "name": "Brute force", "time": "O(n^2)", "space": "O(1)", "status": "verified",
         "key_idea": "try every subarray", "python_code": "def max_subarray(nums):\n    return 1",
         "tests_passed": 300, "exhaustive": False},
        {"id": "a2", "name": "Broken", "time": "O(n)", "space": "O(1)", "status": "failed",
         "key_idea": "?", "python_code": "SECRET_UNVERIFIED_CODE", "reason": "wrong on [1]"},
    ],
}  # fmt: skip


def test_problem_context_leaves_out_unverified_code():
    ctx = problem_context(VIEW, focus="a1")
    assert "Max Subarray" in ctx and "the one the learner is looking at" in ctx
    assert "Verified on 300 tests" in ctx and "Kadane's algorithm" in ctx
    assert "SECRET_UNVERIFIED_CODE" not in ctx and "Not verified" in ctx


def test_checker_problems_cant_be_checked():
    with pytest.raises(NotCheckable):
        problem_target({"comparator": {"kind": "checker"}}, [], None, 1)
    with pytest.raises(NotCheckable):
        problem_target({"comparator": {"kind": "exact"}}, [], None, 1)


# --- check my code, in the real sandbox -------------------------------------------------------

needs_sandbox = pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")


def check(api, code):
    return api.post("/api/chat/check", json={"context": {"kind": "library", "id": "kadane"},
                                             "code": code})  # fmt: skip


@needs_sandbox
def test_check_passes_correct_code(api):
    out = check(api, KADANE).json()
    assert out["verdict"] == "passed" and out["passed"] == out["total"] > 20


@needs_sandbox
def test_check_finds_the_first_different_answer(api):
    buggy = KADANE.replace("best = nums[0]", "best = 0")  # wrong when every number is negative
    out = check(api, buggy).json()
    assert out["verdict"] == "wrong" and out["passed"] < out["total"]
    f = out["failure"]
    assert max(f["input"][0]) < 0 and f["got"] == 0 and f["expected"] == max(f["input"][0])
    assert "verified solution gives" in out["message"]


@needs_sandbox
def test_check_reports_errors_and_slow_code(api):
    crash = check(api, "def max_subarray(nums):\n    return nums[10**6]\n").json()
    assert crash["verdict"] == "runtime_error" and "IndexError" in crash["message"]
    slow = check(api, "def max_subarray(nums):\n    while True:\n        pass\n").json()
    assert slow["verdict"] == "timeout"
    missing = check(api, "def something_else(nums):\n    return 0\n").json()
    assert missing["verdict"] == "missing_function" and "max_subarray" in missing["message"]


def test_tutor_out_of_allowance_says_so(api, monkeypatch):
    from algolens.ai.client import QuotaExhausted

    def out(role, system, transcript):
        raise QuotaExhausted("groq", "m", 1800, True, "HTTP 429: tokens per day")

    monkeypatch.setattr(chat_api, "client_from_settings",
                        lambda: AIClient({"tutor": "fake:t"}, fake=out))  # fmt: skip
    r = ask(api, "hi")
    assert r.status_code == 503
    assert r.json()["detail"].startswith("Today's free AI allowance has run out, so the tutor")
    assert "30 minutes" in r.json()["detail"]
