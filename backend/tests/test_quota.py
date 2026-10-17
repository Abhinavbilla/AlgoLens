"""When a free AI tier's allowance runs out, learners get a plain message with when it's back,
not a provider error."""

from datetime import UTC, datetime

import pytest

from algolens.ai import client as ai_client
from algolens.ai.client import QuotaExhausted, _gave_up, _quota, _Retryable, human_wait

GROQ_TPD = (
    'HTTP 429: {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in '
    "organization `org_x` service tier `on_demand` on tokens per day (TPD): Limit 200000, "
    'Used 199500, Requested 3000. Please try again in 1h2m30.5s.","type":"tokens"}}'
)
GROQ_TPM = (
    'HTTP 429: {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` on '
    "tokens per minute (TPM): Limit 8000, Used 7000, Requested 3000. Please try again in "
    '7.5s.","type":"tokens"}}'
)
GEMINI_RPD = (
    'HTTP 429: {"error":{"code":429,"message":"You exceeded your current quota.",'
    '"status":"RESOURCE_EXHAUSTED","details":[{"@type":"type.googleapis.com/'
    'google.rpc.QuotaFailure","violations":[{"quotaId":'
    '"GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}'
)


def test_groq_daily_limit_is_used_up_with_its_wait():
    q = _quota("groq", "openai/gpt-oss-120b", _Retryable(GROQ_TPD))
    assert isinstance(q, QuotaExhausted) and q.daily
    assert 3740 <= q.wait_s <= 3760  # 1h2m30.5s, from the message
    assert q.retry_at > datetime.now(UTC)


def test_retry_after_header_wins_and_a_long_wait_counts_too():
    q = _quota("groq", "m", _Retryable(GROQ_TPM, wait=900))  # 15 minutes: not worth waiting
    assert isinstance(q, QuotaExhausted) and not q.daily and q.wait_s == 900


def test_per_minute_limit_is_just_retried():
    assert _quota("groq", "m", _Retryable(GROQ_TPM)) is None  # 7.5 s: wait and retry
    assert _quota("groq", "m", _Retryable("HTTP 503: overloaded", wait=900)) is None
    assert _quota("groq", "m", _Retryable("network error: timed out")) is None


def test_gemini_daily_quota_resets_at_pacific_midnight():
    q = _quota("gemini", "gemini-3.8-flash", _Retryable(GEMINI_RPD))
    assert isinstance(q, QuotaExhausted) and q.daily
    assert 0 < q.wait_s <= 24 * 3600


def test_giving_up_on_repeated_429s_is_a_quota_error():
    assert isinstance(_gave_up("groq", "m", GROQ_TPM), QuotaExhausted)
    assert not isinstance(_gave_up("groq", "m", "HTTP 503: down"), QuotaExhausted)


def test_learners_get_a_plain_message():
    q = QuotaExhausted("groq", "m", 3 * 3600 + 10 * 60, True, GROQ_TPD)
    text = q.friendly("This problem couldn't be solved")
    assert text.startswith("Today's free AI allowance has run out, so this problem couldn't")
    assert "about 3 h 10 min" in text and "library" in text
    assert "groq" not in text.lower() and "429" not in text  # no provider jargon
    unknown = QuotaExhausted("gemini", "m", None, True, "").friendly("The tutor can't answer")
    assert "back later today" in unknown and q.retry_at is not None


@pytest.mark.parametrize(("seconds", "words"), [
    (None, "a minute"), (45, "a minute"), (600, "10 minutes"), (3600, "1 h"),
    (5400, "1 h 30 min"),
])  # fmt: skip
def test_human_wait(seconds, words):
    assert human_wait(seconds) == words


def test_the_client_raises_it_instead_of_waiting(monkeypatch):
    """A long Retry-After never makes a request sleep for an hour."""
    c = ai_client.AIClient({"parse": "groq:m"})
    monkeypatch.setenv("GROQ_API_KEY", "x")

    def refuse(url, body, headers):
        raise _Retryable(GROQ_TPD, wait=3700)

    monkeypatch.setattr(c, "_post", refuse)
    monkeypatch.setattr(ai_client.time, "sleep", lambda s: pytest.fail("shouldn't wait"))
    with pytest.raises(QuotaExhausted):
        c.complete_json("parse", "sys", "prompt", ai_client.Budget(100_000))
