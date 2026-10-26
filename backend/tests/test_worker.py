import pytest
from sqlalchemy import create_engine, delete, select

from algolens.db.models import Job
from algolens.db.session import session_factory
from algolens.worker import claim_next_job, run_one


@pytest.fixture
def sessions(db_url):
    engine = create_engine(db_url)
    factory = session_factory(engine)
    with factory() as s:
        s.execute(delete(Job))
        s.commit()
    yield factory
    engine.dispose()


def _enqueue(sessions, kind: str) -> Job:
    with sessions() as s:
        job = Job(kind=kind)
        s.add(job)
        s.commit()
        return job


def test_empty_queue(sessions):
    assert run_one(sessions) is False


def test_unknown_kind_is_failed_not_dropped(sessions, caplog):
    job = _enqueue(sessions, "mystery")
    assert run_one(sessions, handlers={}) is True
    with sessions() as s:
        done = s.get(Job, job.id)
        assert done.status == "failed" and done.payload["error_kind"] == "internal"
        # The learner reads a plain message; the technical detail goes to the log.
        assert "no handler" not in done.error and "Something broke" in done.error
        assert "no handler" in caplog.text
        assert done.started_at is not None and done.finished_at is not None


def test_handler_runs_and_marks_done(sessions):
    job = _enqueue(sessions, "echo")
    seen = []
    run_one(sessions, handlers={"echo": lambda _s, j: seen.append(j.id)})
    assert seen == [job.id]
    with sessions() as s:
        assert s.get(Job, job.id).status == "done"


def test_locked_job_is_skipped_by_second_worker(sessions):
    _enqueue(sessions, "a")
    with sessions() as first, sessions() as second:
        # First worker holds the row lock (no commit yet), second must not see it.
        first_job = first.scalars(select(Job).with_for_update(skip_locked=True)).first()
        assert first_job is not None
        assert claim_next_job(second) is None
        first.rollback()


def test_jobs_left_running_by_a_stopped_worker_are_failed(sessions):
    from algolens.worker import INTERRUPTED, fail_interrupted

    with sessions() as s:
        s.add(Job(kind="solve", status="running", payload={"text": "secret", "text_hash": "h"}))
        s.add(Job(kind="solve", status="queued"))
        s.commit()
        assert fail_interrupted(s) == 1
    with sessions() as s:
        jobs = {j.status: j for j in s.scalars(select(Job)).all()}
        assert jobs["failed"].error == INTERRUPTED and "text" not in jobs["failed"].payload
        assert "queued" in jobs


def test_used_up_ai_allowance_gives_a_plain_message_and_when_its_back(sessions):
    from algolens.ai.client import QuotaExhausted

    job = _enqueue(sessions, "solve")

    def out_of_quota(_s, _j):
        raise QuotaExhausted("groq", "m", 2 * 3600, True, "HTTP 429: tokens per day (TPD)")

    run_one(sessions, handlers={"solve": out_of_quota})
    with sessions() as s:
        done = s.get(Job, job.id)
        assert done.status == "failed"
        assert done.error.startswith("Today's free AI allowance has run out")
        assert "about 2 h" in done.error and "groq" not in done.error.lower()
        assert done.payload["quota"]["daily"] is True and done.payload["quota"]["retry_at"]
