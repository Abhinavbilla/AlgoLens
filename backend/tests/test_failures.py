"""A failed job tells the learner what went wrong in plain words: never a status code, a
provider's JSON or a validation dump."""

import pytest

from algolens.ai.budget import BudgetExhausted
from algolens.ai.client import AIError, AIUnavailable, QuotaExhausted, _gave_up
from algolens.failures import TextGone, describe_failure
from algolens.pipeline.solve import BadReply, budget_reason
from algolens.sandbox.client import SandboxUnavailable

RAW = ('HTTP 503: {"error":{"code":503,"message":"The model is overloaded.",'
       '"status":"UNAVAILABLE"}}')  # fmt: skip


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (QuotaExhausted("groq", "m", 3600, True, RAW), "quota"),
        (AIUnavailable("the AI service refused the key (HTTP 401: {...})"), "ai_setup"),
        (BadReply("parse: reply didn't fit the required shape: 2 validation errors"), "ai_format"),
        (_gave_up("groq", "m", "reply wasn't a JSON object: '{'"), "ai_format"),
        (AIError("groq kept rejecting the request size for m: Request too large"), "too_big"),
        (_gave_up("gemini", "m", RAW), "ai_down"),
        (SandboxUnavailable("sandbox unreachable: [Errno 2]"), "sandbox"),
        (TextGone("gone"), "lost_text"),
        (KeyError("function_name"), "internal"),
    ],
)
def test_every_failure_has_a_kind_and_a_plain_message(exc, kind):
    got, message = describe_failure(exc)
    assert got == kind
    for leak in ("HTTP", "{", "Errno", "validation error", "KeyError", "function_name"):
        assert leak not in message
    assert message.endswith((".", "!"))


def test_budget_reason_names_the_stage_in_words():
    text = budget_reason(BudgetExhausted("repair", 9000, 100))
    assert "fixing an approach" in text and "9000" not in text and "budget" in text
