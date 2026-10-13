from pathlib import Path

from alembic import command
from alembic.config import Config

from algolens.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", url or get_settings().database_url)
    return cfg


def upgrade(url: str | None = None) -> None:
    command.upgrade(alembic_config(url), "head")


def downgrade_to_base(url: str | None = None) -> None:
    command.downgrade(alembic_config(url), "base")
