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
    assert [e["slug"] for e in entries] == ["bubble-sort", "binary-search", "two-pointers"]
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
