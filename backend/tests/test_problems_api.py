"""Pasted problems through the queue, the database and the API, with scripted AI replies."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select

from algolens.ai.client import AIClient
from algolens.api import app as app_module
from algolens.api import problems as problems_api
from algolens.db import session as session_module
from algolens.db.models import Job, Problem, Run
from algolens.db.session import session_factory
from algolens.pipeline import service
from algolens.sandbox.client import SandboxClient
from algolens.worker import run_one
from tests.test_solve import STATEMENT, happy

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")
ROLES = ("parse", "brute_a", "brute_b", "approaches", "checker", "repair", "narration")


def fake_ai(script=None) -> AIClient:
    return AIClient({r: "fake:test" for r in ROLES}, fake=script or happy())


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


def _solve_handlers(ai: AIClient, socket: str | None):
    def handle(session, job):
        service.handle_solve(session, job, ai=ai, sandbox=SandboxClient(socket))

    return {"solve": handle}


@pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")
def test_solve_job_stores_results_and_never_keeps_the_text(sessions):
    ai = fake_ai()
    with sessions() as s:
        out = service.submit(s, STATEMENT, ai=ai)
        job = s.get(Job, uuid.UUID(out["job_id"]))
        assert job.payload["text"] == service.normalize(STATEMENT)
        # Submitting again while queued joins the same job.
        assert service.submit(s, STATEMENT + "\n", ai=ai) == out

    assert run_one(sessions, handlers=_solve_handlers(ai, SOCKET)) is True

    with sessions() as s:
        job = s.get(Job, uuid.UUID(out["job_id"]))
        assert job.status == "done", job.error
        assert "text" not in job.payload and job.stage == "finished"
        problem_id = uuid.UUID(job.payload["problem_id"])
        view = service.problem_view(s, problem_id)
        assert view["status"] == "done" and view["title"] == "Maximum Subarray"
        assert [a["status"] for a in view["approaches"]] == ["verified", "verified"]
        assert view["approaches"][0]["is_brute"] and view["approaches"][1]["tests_passed"] == 300
        run = s.scalar(select(Run).where(Run.problem_id == problem_id))
        assert run.status == "done" and run.tokens["used"] > 0 and run.stage_timings
        # Nothing stored anywhere contains the statement itself.
        problem = s.get(Problem, problem_id)
        assert problem.text_hash == service.text_hash(STATEMENT)
        assert "largest sum" not in str(problem.spec)
        # Cached: the same text is answered from storage, no new job.
        assert service.submit(s, STATEMENT, ai=ai) == {"problem_id": str(problem_id)}


def test_failed_job_still_loses_the_text_and_records_the_error(sessions, tmp_path):
    ai = fake_ai()
    with sessions() as s:
        out = service.submit(s, STATEMENT, ai=ai)
    # A sandbox that isn't there: an error for the job, never a verdict on the problem.
    assert run_one(sessions, handlers=_solve_handlers(ai, str(tmp_path / "nope.sock"))) is True
    with sessions() as s:
        job = s.get(Job, uuid.UUID(out["job_id"]))
        assert job.status == "failed" and job.error
        assert "text" not in job.payload and "problem_id" not in job.payload
        assert s.scalars(select(Problem)).all() == []
        run = s.scalars(select(Run)).one()
        assert run.status == "error" and run.failure_reasons


def test_unknown_handler_failure_also_strips_text(sessions):
    with sessions() as s:
        s.add(Job(kind="solve", payload={"text": "secret statement", "text_hash": "x"}))
        s.commit()

    def boom(session, job):
        raise RuntimeError("worker crashed early")

    run_one(sessions, handlers={"solve": boom})
    with sessions() as s:
        job = s.scalars(select(Job)).one()
        assert job.status == "failed" and "text" not in job.payload


def test_system_version_changes_with_the_models():
    a = AIClient({r: "fake:one" for r in ROLES})
    b = AIClient({**{r: "fake:one" for r in ROLES}, "repair": "fake:two"})
    assert service.system_version(a) != service.system_version(b)


def test_missing_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "x")
    ai = AIClient({"parse": "gemini:m", "brute_b": "groq:m", "repair": "fake:x"})
    assert service.missing_keys(ai) == ["GEMINI_API_KEY"]


def test_text_hash_ignores_line_endings_and_trailing_space():
    assert service.text_hash("a  \r\nb\n") == service.text_hash("a\nb")
    assert service.text_hash("a\nb") != service.text_hash("a\nc")


# --- HTTP ----------------------------------------------------------------------------------


@pytest.fixture
def api(sessions):
    return TestClient(app_module.create_app())


def test_post_needs_keys(api, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = api.post("/api/problems", json={"text": STATEMENT})
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]


def test_post_validates_length(api, monkeypatch):
    monkeypatch.setattr(problems_api, "missing_keys", lambda ai=None: [])
    assert api.post("/api/problems", json={"text": "too short"}).status_code == 422
    assert api.post("/api/problems", json={"text": "x" * 10_001}).status_code == 422


def test_post_queues_a_job_and_reports_it(api, monkeypatch, sessions):
    monkeypatch.setattr(problems_api, "missing_keys", lambda ai=None: [])
    r = api.post("/api/problems", json={"text": STATEMENT})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    view = api.get(f"/api/jobs/{job_id}").json()
    assert view["status"] == "queued" and view["stage"] == "waiting in the queue"
    assert "text" not in view
    # The event stream ends once the job is finished.
    with sessions() as s:
        job = s.get(Job, uuid.UUID(job_id))
        job.status, job.error, job.payload = "failed", "boom", {}
        s.commit()
    body = api.get(f"/api/jobs/{job_id}/events").text
    assert body.startswith("data: ") and '"status": "failed"' in body


def test_unknown_ids_are_404(api):
    assert api.get(f"/api/jobs/{uuid.uuid4()}").status_code == 404
    assert api.get(f"/api/jobs/{uuid.uuid4()}/events").status_code == 404
    assert api.get(f"/api/problems/{uuid.uuid4()}").status_code == 404
