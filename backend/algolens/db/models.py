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
