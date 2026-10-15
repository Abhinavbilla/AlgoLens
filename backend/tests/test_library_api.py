"""Library end to end: seed into Postgres, verify in the real sandbox, serve animations."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from algolens.api import app as app_module
from algolens.config import get_settings
from algolens.db import session as session_module
from algolens.library.loader import load_all, seed
from algolens.library.verify import verify_entry
from algolens.sandbox.client import SandboxClient

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")


@pytest.fixture
def client(db_url, monkeypatch):
    if not SOCKET:
        pytest.skip("ALGOLENS_TEST_SANDBOX_SOCKET not set")
    engine = create_engine(db_url)
    monkeypatch.setattr(session_module, "get_engine", lambda url=None: engine)
    monkeypatch.setenv("ALGOLENS_SANDBOX_SOCKET", SOCKET)
    get_settings.cache_clear()
    with session_module.session_factory(engine)() as s:
        seed(s, load_all(get_settings().library_dir))
    yield TestClient(app_module.create_app())
    get_settings.cache_clear()
    engine.dispose()


def test_every_library_entry_verifies():
    if not SOCKET:
        pytest.skip("ALGOLENS_TEST_SANDBOX_SOCKET not set")
    sandbox = SandboxClient(SOCKET)
    for entry in load_all(get_settings().library_dir):
        result = verify_entry(entry, sandbox)
        assert result["status"] == "verified", (entry.slug, result["failures"])
        assert result["narration"]["coverage"] >= 0.9, entry.slug
    sandbox.close()


def test_list_and_entry(client):
    entries = client.get("/api/library").json()
    # Listed in the entries' declared order (test_animation pins the full list).
    expected = sorted(load_all(get_settings().library_dir), key=lambda e: (e.order, e.slug))
    assert [e["slug"] for e in entries] == [e.slug for e in expected]
    assert len(entries) == 33
    assert entries[0]["verification"]["status"] == "unverified"  # until `library verify` runs
    entry = client.get("/api/library/binary-search").json()
    assert entry["python_code"].startswith("def lower_bound")


def test_animation_is_a_faithful_recording(client):
    resp = client.get("/api/library/two-pointers/animation")
    assert resp.status_code == 200
    anim = resp.json()
    assert anim["result"] == [2, 4]
    frames = anim["frames"]
    assert 0 < len(frames) <= 300
    assert [f["ops"] for f in frames] == list(range(1, len(frames) + 1))
    assert frames[-1]["next"] == "return"
    assert all(f["narration"]["text"] for f in frames)


def test_unknown_entry_is_404(client):
    assert client.get("/api/library/nope").status_code == 404
    assert client.get("/api/library/nope/animation").status_code == 404


def test_verification_catches_a_planted_bug():
    if not SOCKET:
        pytest.skip("ALGOLENS_TEST_SANDBOX_SOCKET not set")
    from dataclasses import replace

    entry = next(e for e in load_all(get_settings().library_dir) if e.slug == "bubble-sort")
    # Each pass stops one position early: wrong only for some inputs, and the hand-written
    # tests don't all catch it, so the random tests have to.
    buggy = replace(
        entry, python_code=entry.python_code.replace("range(n - 1 - i)", "range(n - 2 - i)")
    )
    assert buggy.python_code != entry.python_code
    sandbox = SandboxClient(SOCKET)
    result = verify_entry(buggy, sandbox)
    sandbox.close()
    assert result["status"] == "failed"
    assert any("python gave" in f for f in result["failures"])


def test_custom_input_runs(client):
    resp = client.post("/api/library/binary-search/animation", json={"args": [[2, 4, 6], 5]})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["result"] == 2
    assert resp.json()["input"] == {"args": [[2, 4, 6], 5]}


def test_custom_input_breaking_the_schema_never_runs(client):
    resp = client.post("/api/library/binary-search/animation", json={"args": [[5, 1], 3]})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["issues"] == [
        {"path": "nums", "message": "must be sorted in ascending order (nums[1] = 1 comes after 5)"}
    ]


def test_custom_input_breaking_the_validator_rule(client):
    resp = client.post("/api/library/two-pointers/animation", json={"args": [[1, 2, 3, 4], 5]})
    assert resp.status_code == 422
    assert "more than one pair adds up to 5" in resp.json()["detail"]["issues"][0]["message"]


def test_custom_input_too_long_asks_for_a_smaller_one(client):
    resp = client.post(
        "/api/library/bubble-sort/animation", json={"args": [list(range(30, 0, -1))]}
    )
    assert resp.status_code == 422
    assert "Try a smaller input" in resp.json()["detail"]["message"]


def test_entry_describes_its_inputs(client):
    params = client.get("/api/library/binary-search").json()["params"]
    assert [p["name"] for p in params] == ["nums", "target"]
    assert params[0]["hint"].startswith("a sorted list of 0 to 1000 values")
