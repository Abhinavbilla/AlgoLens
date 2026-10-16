from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from algolens.animation.service import (
    AnimationError,
    TraceFailed,
    cached_animation,
)
from algolens.db.models import LibraryEntry
from algolens.db.session import session_factory
from algolens.library.loader import EntrySource, from_row
from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.describe import describe
from algolens.schema.model import compile_schema
from algolens.schema.service import check_input

router = APIRouter(prefix="/api/library", tags=["library"])
UNAVAILABLE = "The code runner is unavailable right now. Stored animations still work."


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
    return {
        k: v.get(k) for k in ("status", "checked_at", "method", "tests", "random_tests", "failures")
    }


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
    schema = compile_schema(c["schema"])
    return {
        "slug": row.slug,
        "title": row.title,
        "category": row.category,
        "summary": c["summary"],
        "entry": c["entry"],
        "description": row.description,
        "note": c.get("note", ""),
        "python_code": c["python_code"],
        "cpp_code": c["cpp_code"],
        "default_input": c["default_input"],
        "params": [
            {
                "name": p.name,
                "kind": c["schema"]["params"][i]["type"]["kind"],
                "hint": describe(p.type),
            }
            for i, p in enumerate(schema.params)
        ],  # fmt: skip
        "verification": _verification(row),
    }


def _animation_or_error(entry: EntrySource, args_input: dict, custom: bool) -> dict:
    try:
        return cached_animation(entry, args_input)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail={"message": UNAVAILABLE, "issues": []}) from exc
    except AnimationError as exc:
        if exc.code == "too_long" and custom:
            message = f"This input takes too many steps to animate ({exc}). Try a smaller input."
        else:
            message = str(exc)
        raise HTTPException(422, detail={"message": message, "issues": []}) from exc
    except TraceFailed as exc:
        if exc.status == "trace_failed" and custom:
            message = "This input is too big to record step by step. Try a smaller one."
        elif exc.status in ("runtime_error", "timeout", "memory", "output_limit"):
            message = f"The solution couldn't run on this input ({exc.status}: {exc.detail})."
        else:
            message = f"Couldn't record this run: {exc.detail or exc.status}"
        raise HTTPException(422, detail={"message": message, "issues": []}) from exc


@router.get("/{slug}/animation")
def get_animation(slug: str) -> dict:
    entry = from_row(_row(slug))
    return _animation_or_error(entry, entry.default_input, custom=False)


class CustomInput(BaseModel):
    args: list


@router.post("/{slug}/animation")
def post_animation(slug: str, body: CustomInput) -> dict:
    """Animate a learner's own input. It's checked against the problem's input rules first;
    if it breaks them, nothing runs and the response says what's wrong."""
    entry = from_row(_row(slug))
    client = SandboxClient()
    try:
        issues = check_input(entry.rules(), body.args, client)
    except SandboxUnavailable as exc:
        raise HTTPException(503, detail={"message": UNAVAILABLE, "issues": []}) from exc
    finally:
        client.close()
    if issues:
        raise HTTPException(422, detail={
            "message": "This input doesn't fit the problem.",
            "issues": [{"path": i.path, "message": i.message} for i in issues],
        })  # fmt: skip
    return _animation_or_error(entry, {"args": body.args}, custom=True)
