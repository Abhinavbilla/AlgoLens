"""Initial tables: problems, approaches, runs, jobs, library_entries.

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _ts(name: str, nullable: bool = False) -> sa.Column:
    default = None if nullable else sa.func.now()
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable, server_default=default)


def upgrade() -> None:
    op.create_table(
        "problems",
        _id(),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("system_version", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("spec", JSONB()),
        sa.Column("rejection_reason", sa.Text()),
        _ts("created_at"),
        sa.UniqueConstraint("text_hash", "system_version"),
    )
    op.create_table(
        "approaches",
        _id(),
        sa.Column(
            "problem_id",
            sa.Uuid(),
            sa.ForeignKey("problems.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_idea", sa.Text(), nullable=False),
        sa.Column("time_complexity", sa.String(64), nullable=False),
        sa.Column("space_complexity", sa.String(64), nullable=False),
        sa.Column("python_code", sa.Text(), nullable=False),
        sa.Column("cpp_code", sa.Text(), nullable=False),
        sa.Column("py_to_cpp_lines", JSONB()),
        sa.Column("visual_spec", JSONB()),
        sa.Column("narration_templates", JSONB()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("verification", JSONB()),
        _ts("created_at"),
    )
    op.create_table(
        "runs",
        _id(),
        sa.Column(
            "problem_id",
            sa.Uuid(),
            sa.ForeignKey("problems.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage_timings", JSONB(), nullable=False),
        sa.Column("tokens", JSONB(), nullable=False),
        sa.Column("failure_reasons", JSONB(), nullable=False),
        _ts("started_at"),
        _ts("finished_at", nullable=True),
    )
    op.create_table(
        "jobs",
        _id(),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stage", sa.String(64)),
        sa.Column("tests_passed", sa.Integer(), nullable=False),
        sa.Column("tests_total", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        _ts("created_at"),
        _ts("started_at", nullable=True),
        _ts("finished_at", nullable=True),
    )
    op.create_index("ix_jobs_status_created", "jobs", ["status", "created_at"])
    op.create_table(
        "library_entries",
        _id(),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("verification", JSONB()),
        _ts("updated_at"),
    )


def downgrade() -> None:
    op.drop_table("library_entries")
    op.drop_index("ix_jobs_status_created", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("runs")
    op.drop_table("approaches")
    op.drop_table("problems")
