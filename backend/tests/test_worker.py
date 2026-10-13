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


def test_unknown_kind_is_failed_not_dropped(sessions):
    job = _enqueue(sessions, "mystery")
    assert run_one(sessions, handlers={}) is True
    with sessions() as s:
        done = s.get(Job, job.id)
        assert done.status == "failed"
        assert "no handler" in done.error
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
