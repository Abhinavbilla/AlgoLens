"""Job worker. Claims queued jobs with SKIP LOCKED so several workers can run safely.

No job kinds exist yet (the pipeline arrives in M5); unknown kinds are failed, not dropped.
"""

import logging
import signal
import time
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from algolens.config import get_settings
from algolens.db.models import Job
from algolens.db.session import session_factory

log = logging.getLogger("algolens.worker")

Handler = Callable[[Session, Job], None]
HANDLERS: dict[str, Handler] = {}


def claim_next_job(session: Session) -> Job | None:
    job = session.scalars(
        select(Job)
        .where(Job.status == "queued")
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if job is not None:
        job.status = "running"
        job.started_at = func.now()
        session.commit()
    return job


def run_one(sessions: sessionmaker[Session], handlers: dict[str, Handler] = HANDLERS) -> bool:
    """Process at most one job. Returns False when the queue was empty."""
    with sessions() as session:
        job = claim_next_job(session)
        if job is None:
            return False
        handler = handlers.get(job.kind)
        try:
            if handler is None:
                raise LookupError(f"no handler for job kind {job.kind!r}")
            handler(session, job)
            job.status = "done"
        except Exception as exc:
            session.rollback()
            log.exception("job %s failed", job.id)
            job.status = "failed"
            job.error = str(exc)
        job.finished_at = func.now()
        session.commit()
        return True


def run_forever() -> None:
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    sessions = session_factory()
    poll = get_settings().worker_poll_seconds
    log.info("worker started")
    while not stopping:
        try:
            if not run_one(sessions):
                time.sleep(poll)
        except Exception:
            log.exception("worker loop error; retrying")
            time.sleep(poll)
    log.info("worker stopped")
