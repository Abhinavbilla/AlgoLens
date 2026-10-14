import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from algolens.db.session import database_is_up

TEST_DB_URL = os.environ.get("ALGOLENS_TEST_DATABASE_URL")


def _ensure_database(url: str) -> None:
    """Create the test database if the server is up but the database doesn't exist yet."""
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    except Exception:
        pass  # server unreachable: the caller skips
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def db_url() -> str:
    """A migrated, empty test database. Tests using this are skipped when none is reachable."""
    if not TEST_DB_URL:
        pytest.skip("ALGOLENS_TEST_DATABASE_URL not set")
    _ensure_database(TEST_DB_URL)
    engine = create_engine(TEST_DB_URL)
    if not database_is_up(engine):
        pytest.skip(f"test database not reachable: {TEST_DB_URL}")
    from algolens.db.migrate import downgrade_to_base, upgrade

    downgrade_to_base(TEST_DB_URL)
    upgrade(TEST_DB_URL)
    engine.dispose()
    return TEST_DB_URL
