from alembic import command

from algolens.db.migrate import alembic_config, downgrade_to_base, upgrade


def test_models_match_migrations(db_url):
    # Raises if the ORM models have drifted from the migration history.
    command.check(alembic_config(db_url))


def test_downgrade_and_upgrade_round_trip(db_url):
    downgrade_to_base(db_url)
    upgrade(db_url)
    command.check(alembic_config(db_url))
