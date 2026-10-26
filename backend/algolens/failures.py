"""What a learner reads when a job fails: what went wrong, in plain words, and what to do.

The exception itself (provider replies, status codes, validation dumps) goes to the logs and
the run record, never to the page. Each failure also gets a kind, so the page can title it.
"""

from algolens.ai.client import AIError, AIUnavailable, QuotaExhausted
from algolens.sandbox.client import SandboxUnavailable

NOTHING_JUDGED = "Nothing about your problem was marked right or wrong because of it."


class TextGone(Exception):
    """The pasted text left the database before the job could use it."""


def describe_failure(exc: BaseException) -> tuple[str, str]:
    """(kind, message) for a job that stopped with `exc`."""
    from algolens.pipeline.solve import BadReply

    if isinstance(exc, QuotaExhausted):
        return "quota", exc.friendly("This problem couldn't be solved")
    if isinstance(exc, AIUnavailable):
        return "ai_setup", (
            "AlgoLens couldn't use its AI service: the service didn't accept this server's "
            "access key, or the key isn't set up. This is a problem on our side, not with your "
            f"statement, so trying again won't help until it's fixed. {NOTHING_JUDGED}"
        )
    if isinstance(exc, BadReply) or (
        isinstance(exc, AIError) and "wasn't a JSON object" in str(exc)
    ):
        return "ai_format", (
            "The AI kept replying in a form AlgoLens couldn't use, so we stopped before running "
            f"anything. This happens now and then; trying again usually works. {NOTHING_JUDGED}"
        )
    if isinstance(exc, AIError) and "request size" in str(exc):
        return "too_big", (
            "This statement is too long for the free AI service to handle in one request. Try "
            "pasting just the statement, the examples and the constraints, without extra notes "
            f"or long stories. {NOTHING_JUDGED}"
        )
    if isinstance(exc, AIError):
        return "ai_down", (
            "The AI service isn't responding properly right now: it was unreachable or kept "
            "returning errors after several tries. Wait a few minutes and try again. "
            f"{NOTHING_JUDGED}"
        )
    if isinstance(exc, SandboxUnavailable):
        return "sandbox", (
            "The code runner that tests every solution is down right now, so nothing could be "
            f"checked. Wait a few minutes and try again. {NOTHING_JUDGED}"
        )
    if isinstance(exc, TextGone):
        return "lost_text", (
            "The server lost your pasted statement before it could start (usually because it "
            "restarted). Please paste it again."
        )
    return "internal", (
        "Something broke inside AlgoLens while solving this. It has been logged for us to look "
        f"at. Trying again may work; if it keeps happening, the problem may be one AlgoLens "
        f"can't handle yet. {NOTHING_JUDGED}"
    )
