"""Core tables (plan §4). Shapes will grow per milestone via new migrations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
        datetime: DateTime(timezone=True),
    }


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(server_default=func.now())


class Problem(Base):
    """A processed problem. Only the hash of the pasted text is kept, never the text."""

    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("text_hash", "system_version"),)

    id: Mapped[uuid.UUID] = _pk()
    text_hash: Mapped[str] = mapped_column(String(64))
    system_version: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    spec: Mapped[dict[str, Any] | None]
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()


class Approach(Base):
    __tablename__ = "approaches"

    id: Mapped[uuid.UUID] = _pk()
    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    name: Mapped[str] = mapped_column(Text)
    key_idea: Mapped[str] = mapped_column(Text)
    time_complexity: Mapped[str] = mapped_column(String(64))
    space_complexity: Mapped[str] = mapped_column(String(64))
    python_code: Mapped[str] = mapped_column(Text)
    cpp_code: Mapped[str] = mapped_column(Text)
    py_to_cpp_lines: Mapped[dict[str, Any] | None]
    visual_spec: Mapped[dict[str, Any] | None]
    narration_templates: Mapped[list[Any] | None]
    status: Mapped[str] = mapped_column(String(32))
    verification: Mapped[dict[str, Any] | None]
    created_at: Mapped[datetime] = _created()


class Run(Base):
    """One pipeline execution: per-stage timings, tokens and failure reasons (for eval)."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = _pk()
    problem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("problems.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32))
    stage_timings: Mapped[dict[str, Any]] = mapped_column(default=dict)
    tokens: Mapped[dict[str, Any]] = mapped_column(default=dict)
    failure_reasons: Mapped[list[Any]] = mapped_column(default=list)
    started_at: Mapped[datetime] = _created()
    finished_at: Mapped[datetime | None]


class Job(Base):
    """Work queue, claimed with SELECT ... FOR UPDATE SKIP LOCKED."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = _pk()
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    stage: Mapped[str | None] = mapped_column(String(64))
    tests_passed: Mapped[int] = mapped_column(default=0)
    tests_total: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class LibraryEntry(Base):
    __tablename__ = "library_entries"

    id: Mapped[uuid.UUID] = _pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    content: Mapped[dict[str, Any]]
    verification: Mapped[dict[str, Any] | None]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# --- optional Google accounts (migration 0002) ---------------------------------------------


class User(Base):
    """Someone who chose to sign in, with Google or an emailed code. No passwords."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    # Google's stable user id; None for someone who has only signed in by email.
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)  # always lowercase
    name: Mapped[str] = mapped_column(Text)
    picture: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    last_seen_at: Mapped[datetime] = _created()


class Session(Base):
    """A signed-in browser. Only a hash of the cookie's token is stored."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _pk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime]


class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    done: Mapped[list[Any]] = mapped_column(default=list)  # library slugs and primer ids
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class UserProblem(Base):
    """A problem a signed-in learner has opened (the problem's id, never its text)."""

    __tablename__ = "user_problems"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = _created()


class EmailCode(Base):
    """A one-time sign-in code that was emailed. Only its hash is kept, for 10 minutes."""

    __tablename__ = "email_codes"

    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(server_default="0", default=0)
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime]
