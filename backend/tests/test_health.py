from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from algolens import __version__
from algolens.api import app as app_module
from algolens.db import session as session_module


def test_health_reports_database_down(monkeypatch):
    dead = create_engine(
        "postgresql+psycopg://x:x@127.0.0.1:1/x", connect_args={"connect_timeout": 1}
    )
    monkeypatch.setattr(app_module, "database_is_up", lambda: session_module.database_is_up(dead))
    res = TestClient(app_module.create_app()).get("/api/health")
    assert res.status_code == 503
    assert res.json() == {"status": "degraded", "version": __version__, "database": "down"}


def test_health_ok_with_database(db_url, monkeypatch):
    engine = create_engine(db_url)
    monkeypatch.setattr(app_module, "database_is_up", lambda: session_module.database_is_up(engine))
    res = TestClient(app_module.create_app()).get("/api/health")
    assert res.status_code == 200
    assert res.json()["database"] == "ok"
