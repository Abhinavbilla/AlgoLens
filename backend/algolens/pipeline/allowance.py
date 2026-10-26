"""How many new problems a visitor may solve a day, and where a job stands in the queue.

Free AI tiers allow only so many problems a day for the whole site, so each visitor gets a
share: a signed-in learner by account, anyone else by a hash of their address (the address
itself is never stored). Only a problem that was *delivered* counts against it: solved, with
at least one verified approach (code, animation and output to learn from). A job that failed
or was turned down, or a result that was already cached, costs nothing. The count comes from
the jobs table over the last 24 hours, so it survives restarts.

Jobs still waiting or running count too, so nobody can queue up ten problems at once; one
that then fails gives its place back.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from algolens.db.models import Job

WINDOW = timedelta(hours=24)
TYPICAL_SOLVE_S = 180  # until there are finished jobs to measure
IN_FLIGHT = ("queued", "running")


def visitor_key(user_id: str | None, address: str) -> str:
    if user_id:
        return f"user:{user_id}"
    return "ip:" + hashlib.sha256(f"algolens-visitor:{address}".encode()).hexdigest()[:24]


@dataclass
class Allowance:
    limit: int
    used: int  # problems delivered in the last 24 hours
    in_progress: int  # this visitor's jobs still waiting or running
    retry_at: datetime | None  # when the oldest delivered one stops counting

    @property
    def left(self) -> int:
        return max(0, self.limit - self.used - self.in_progress)

    def view(self) -> dict:
        return {
            "limit": self.limit, "used": self.used, "in_progress": self.in_progress,
            "left": self.left, "retry_at": self.retry_at.isoformat() if self.retry_at else None,
        }  # fmt: skip


class DailyLimitReached(Exception):
    def __init__(self, allowance: Allowance):
        self.allowance = allowance
        super().__init__(limit_message(allowance))


def allowance(session: Session, visitor: str, limit: int, now: datetime | None = None) -> Allowance:
    now = now or datetime.now(UTC)
    mine = (Job.kind == "solve", Job.payload["visitor"].astext == visitor)
    delivered = session.scalars(
        select(Job.finished_at)
        .where(*mine, Job.status == "done", Job.payload["delivered"].as_boolean(),
               Job.finished_at > now - WINDOW)
        .order_by(Job.finished_at)
    ).all()  # fmt: skip
    in_progress = session.scalar(
        select(func.count()).select_from(Job).where(*mine, Job.status.in_(IN_FLIGHT))
    )
    retry_at = delivered[0] + WINDOW if len(delivered) >= limit and delivered else None
    return Allowance(limit, len(delivered), in_progress or 0, retry_at)


def limit_message(a: Allowance) -> str:
    """For learners: why they can't paste another one now, and when they can."""
    if a.used >= a.limit:
        when = ""
        if a.retry_at:
            wait = (a.retry_at - datetime.now(UTC)).total_seconds()
            when = f" You can solve a new one in about {_human(wait)}."
        return (
            f"Today's limit is finished: you've solved {a.used} new problem"
            f"{'s' if a.used != 1 else ''} in the last 24 hours, the most each learner gets "
            f"while AlgoLens runs on a free AI allowance.{when} Everything you've already "
            "solved, the library and all the animations still work."
        )
    return (
        f"You already have {a.in_progress} problem{'s' if a.in_progress != 1 else ''} being "
        f"solved, which uses up today's limit of {a.limit}. Wait for "
        f"{'it' if a.in_progress == 1 else 'them'} to finish: if one fails, it doesn't count, "
        "and you can paste another."
    )


def _human(seconds: float) -> str:
    minutes = max(1, round(seconds / 60))
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


def typical_solve_seconds(session: Session) -> float:
    """How long recent problems took to solve (the median of the last 20)."""
    rows = session.execute(
        select(Job.started_at, Job.finished_at)
        .where(Job.kind == "solve", Job.status == "done", Job.started_at.is_not(None),
               Job.finished_at.is_not(None))
        .order_by(Job.finished_at.desc())
        .limit(20)
    ).all()  # fmt: skip
    spans = sorted((f - s).total_seconds() for s, f in rows if f > s)
    return spans[len(spans) // 2] if spans else TYPICAL_SOLVE_S


def queue_position(session: Session, job: Job) -> dict | None:
    """For a waiting job: how many are ahead of it and roughly how long until it starts.
    One worker solves one problem at a time (docker-compose.yml runs a single worker)."""
    if job.status != "queued":
        return None
    waiting = session.scalar(
        select(func.count()).select_from(Job)
        .where(Job.kind == "solve", Job.status == "queued", Job.created_at < job.created_at)
    ) or 0  # fmt: skip
    running = session.scalars(
        select(Job.started_at).where(Job.kind == "solve", Job.status == "running")
    ).all()
    typical = typical_solve_seconds(session)
    now = datetime.now(UTC)
    # The one running now is partway through; each waiting ahead takes a typical run.
    left_running = sum(max(30.0, typical - (now - s).total_seconds()) for s in running if s)
    return {
        "ahead": waiting + len(running),
        "wait_s": round(left_running + waiting * typical),
        "typical_s": round(typical),
    }
