"""The daily limit on new problems counts only delivered results, and a waiting job knows its
place in the queue."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete

from algolens.db import session as session_module
from algolens.db.models import Job, Problem, Run
from algolens.db.session import session_factory
from algolens.pipeline import service
from algolens.pipeline.allowance import (
    DailyLimitReached,
    allowance,
    queue_position,
    visitor_key,
)
from tests.test_problems_api import fake_ai
from tests.test_solve import STATEMENT

ME = visitor_key(None, "203.0.113.7")
NOW = datetime.now(UTC)


@pytest.fixture
def sessions(db_url, monkeypatch):
    engine = create_engine(db_url)
    monkeypatch.setattr(session_module, "get_engine", lambda url=None: engine)
    factory = session_factory(engine)
    with factory() as s:
        for table in (Job, Run, Problem):
            s.execute(delete(table))
        s.commit()
    yield factory
    engine.dispose()


def _job(s, status, visitor=ME, delivered=None, ago=timedelta(hours=1), **extra):
    payload = {"visitor": visitor, "text_hash": "h", "system_version": "v"}
    if delivered is not None:
        payload["delivered"] = delivered
    job = Job(kind="solve", status=status, payload=payload, **extra)
    if status in ("done", "failed"):
        job.started_at, job.finished_at = NOW - ago - timedelta(minutes=3), NOW - ago
    s.add(job)
    s.commit()
    return job


def test_the_address_is_never_stored():
    assert "203.0.113.7" not in ME and visitor_key(None, "203.0.113.7") == ME
    assert visitor_key("u1", "203.0.113.7") == "user:u1"


def test_only_delivered_results_in_the_last_day_count(sessions):
    with sessions() as s:
        _job(s, "done", delivered=True)
        _job(s, "done", delivered=False)  # solved, but nothing verified to show
        _job(s, "failed")  # an error along the way
        _job(s, "done", delivered=True, ago=timedelta(hours=25))  # yesterday's
        _job(s, "done", delivered=True, visitor="user:someone-else")
        a = allowance(s, ME, 3)
        assert (a.used, a.in_progress, a.left, a.retry_at) == (1, 0, 2, None)


def test_waiting_jobs_hold_a_place_and_a_full_day_says_when_it_frees_up(sessions):
    with sessions() as s:
        _job(s, "done", delivered=True, ago=timedelta(hours=20))
        _job(s, "done", delivered=True, ago=timedelta(hours=2))
        _job(s, "queued")
        a = allowance(s, ME, 3)
        assert (a.used, a.in_progress, a.left) == (2, 1, 0)
        full = allowance(s, ME, 2)
        assert abs((full.retry_at - (NOW + timedelta(hours=4))).total_seconds()) < 5


def test_submit_refuses_a_new_problem_but_not_a_cached_one(sessions):
    ai = fake_ai()
    with sessions() as s:
        _job(s, "done", delivered=True)
        with pytest.raises(DailyLimitReached) as caught:
            service.submit(s, STATEMENT, ai=ai, visitor=ME, daily_limit=1)
        assert "Today's limit is finished" in str(caught.value)
        # The same text solved before costs nothing, so it's always given.
        s.add(Problem(text_hash=service.text_hash(STATEMENT), status="done",
                      system_version=service.system_version(ai)))  # fmt: skip
        s.commit()
        assert "problem_id" in service.submit(s, STATEMENT, ai=ai, visitor=ME, daily_limit=1)


def test_a_new_job_remembers_who_asked(sessions):
    with sessions() as s:
        out = service.submit(s, STATEMENT, ai=fake_ai(), visitor=ME, daily_limit=3)
        assert s.get(Job, uuid.UUID(out["job_id"])).payload["visitor"] == ME


def test_queue_position_counts_who_is_ahead(sessions):
    with sessions() as s:
        _job(s, "done", ago=timedelta(hours=1))  # took 3 minutes: the typical time
        _job(s, "running", started_at=NOW - timedelta(minutes=1))
        first = _job(s, "queued", created_at=NOW - timedelta(minutes=2))
        mine = _job(s, "queued", created_at=NOW - timedelta(minutes=1))
        q = queue_position(s, mine)
        assert q["ahead"] == 2 and q["typical_s"] == 180
        assert 290 <= q["wait_s"] <= 310  # 2 minutes left of the running one, then 3
        assert queue_position(s, first)["ahead"] == 1
