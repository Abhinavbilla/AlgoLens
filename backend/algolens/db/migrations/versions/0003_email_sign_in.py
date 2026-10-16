"""Sign-in with an emailed one-time code, alongside Google.

Users may now have no Google id (signed in by email only). Emails are stored lowercased and
are unique, so the same address reaches the same account whichever way someone signs in.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=True)
    op.execute("UPDATE users SET email = lower(email)")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_table(
        "email_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_email_codes_email", "email_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_email_codes_email", table_name="email_codes")
    op.drop_table("email_codes")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.execute("DELETE FROM users WHERE google_sub IS NULL")
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=False)
