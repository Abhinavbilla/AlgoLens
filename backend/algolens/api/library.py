from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from algolens.animation.service import AnimationError, TraceFailed, default_animation
from algolens.db.models import LibraryEntry
from algolens.db.session import session_factory
from algolens.library.loader import from_row
from algolens.sandbox.client import SandboxUnavailable

router = APIRouter(prefix="/api/library", tags=["library"])


def _row(slug: str) -> LibraryEntry:
    with session_factory()() as session:
        row = session.scalar(select(LibraryEntry).where(LibraryEntry.slug == slug))
    if row is None:
        raise HTTPException(404, detail=f"no library entry {slug!r}")
    return row


def _verification(row: LibraryEntry) -> dict:
    v = row.verification
    if not v or v.get("content_hash") != row.content.get("content_hash"):
        return {"status": "unverified"}
    return {k: v[k] for k in ("status", "checked_at", "method", "tests", "failures")}


@router.get("")
def list_entries() -> list[dict]:
    with session_factory()() as session:
        rows = session.scalars(select(LibraryEntry)).all()
    rows = sorted(rows, key=lambda r: (r.content.get("order", 0), r.slug))
    return [
        {"slug": r.slug, "title": r.title, "category": r.category,
         "summary": r.content.get("summary", ""), "verification": _verification(r)}
        for r in rows
    ]  # fmt: skip


@router.get("/{slug}")
def get_entry(slug: str) -> dict:
    row = _row(slug)
    c = row.content
    return {
        "slug": row.slug,
        "title": row.title,
        "category": row.category,
        "summary": c["summary"],
        "description": row.description,
        "note": c.get("note", ""),
        "python_code": c["python_code"],
        "cpp_code": c["cpp_code"],
        "default_input": c["default_input"],
        "verification": _verification(row),
    }


@router.get("/{slug}/animation")
def get_animation(slug: str) -> dict:
    entry = from_row(_row(slug))
    try:
        return default_animation(entry)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail="The code runner is unavailable right now.") from exc
    except TraceFailed as exc:
        raise HTTPException(422, detail=f"Couldn't record this run: {exc.detail}") from exc
    except AnimationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
