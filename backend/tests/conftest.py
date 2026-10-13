import os

import pytest
from sqlalchemy import create_engine

from algolens.db.session import database_is_up

TEST_DB_URL = os.environ.get("ALGOLENS_TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def db_url() -> str:
    """A migrated, empty test database. Tests using this are skipped when none is reachable."""
    if not TEST_DB_URL:
        pytest.skip("ALGOLENS_TEST_DATABASE_URL not set")
    engine = create_engine(TEST_DB_URL)
    if not database_is_up(engine):
        pytest.skip(f"test database not reachable: {TEST_DB_URL}")
    from algolens.db.migrate import downgrade_to_base, upgrade

    downgrade_to_base(TEST_DB_URL)
    upgrade(TEST_DB_URL)
    engine.dispose()
    return TEST_DB_URL
