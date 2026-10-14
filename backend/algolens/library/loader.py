"""Library entries (plan §8): one folder each under library/, seeded into Postgres.

Each folder has solution.py, solution.cpp, reference.py (an independent, simplest-possible
solution the entry is checked against), description.md (written by us), and entry.json
with the title, input schema, tests, default input, visual spec, C++ line map and narration
templates. An optional validator.py holds input rules the schema language can't express.
"""

import ast
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from algolens.animation.builder import AnimationError, compile_visual
from algolens.db.models import LibraryEntry
from algolens.narration.engine import TemplateError, compile_templates
from algolens.schema.model import SchemaError, compile_schema
from algolens.schema.service import InputRules
from algolens.schema.validate import validate

log = logging.getLogger("algolens.library")
REQUIRED = ("title", "category", "summary", "order", "entry", "schema", "default_input",
            "tests", "cpp_lines", "visual", "narration")  # fmt: skip


class LibraryError(ValueError):
    pass


@dataclass(frozen=True)
class EntrySource:
    slug: str
    title: str
    category: str
    summary: str
    order: int
    entry: str
    note: str
    default_input: dict
    tests: list[dict]
    cpp_lines: dict[str, int]
    visual: dict
    narration: list[dict]
    python_code: str
    cpp_code: str
    reference_code: str
    description: str
    schema: dict
    validator_code: str = ""
    result_kind: str = ""  # "binary_tree" / "linked_list" when the solution returns one

    def rules(self) -> InputRules:
        return InputRules(compile_schema(self.schema), self.validator_code or None)

    def sandbox_extras(self) -> dict:
        """Which arguments the sandbox turns into TreeNode / ListNode (from the schema), and
        the result's kind if it's one (so a returned None reads as empty)."""
        kinds = [p["type"]["kind"] for p in self.schema["params"]]
        convert = [k if k in ("binary_tree", "linked_list") else None for k in kinds]
        extras: dict = {"convert": convert} if any(convert) else {}
        if self.result_kind:
            extras["convert_result"] = self.result_kind
        return extras

    @property
    def content_hash(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    def cpp_line_map(self) -> dict[int, int]:
        return {int(k): v for k, v in self.cpp_lines.items()}


def load_entry(folder: Path) -> EntrySource:
    where = f"library/{folder.name}"
    try:
        meta = json.loads((folder / "entry.json").read_text(encoding="utf-8"))
        files = {
            name: (folder / name).read_text(encoding="utf-8")
            for name in ("solution.py", "solution.cpp", "reference.py", "description.md")
        }
    except (OSError, json.JSONDecodeError) as exc:
        raise LibraryError(f"{where}: {exc}") from exc
    missing = [k for k in REQUIRED if k not in meta]
    if missing:
        raise LibraryError(f"{where}: entry.json is missing {missing}")
    entry = EntrySource(
        slug=folder.name,
        title=meta["title"],
        category=meta["category"],
        summary=meta["summary"],
        order=meta["order"],
        entry=meta["entry"],
        note=meta.get("note", ""),
        default_input=meta["default_input"],
        tests=meta["tests"],
        cpp_lines=meta["cpp_lines"],
        visual=meta["visual"],
        narration=meta["narration"],
        python_code=files["solution.py"],
        cpp_code=files["solution.cpp"],
        reference_code=files["reference.py"],
        description=files["description.md"].strip(),
        schema=meta["schema"],
        validator_code=_optional(folder / "validator.py"),
        result_kind=meta.get("result_kind", ""),
    )
    _check(entry, where)
    return entry


def _optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _check(entry: EntrySource, where: str) -> None:
    defined = {n.name for n in ast.parse(entry.python_code).body if isinstance(n, ast.FunctionDef)}
    if entry.entry not in defined:
        raise LibraryError(f"{where}: solution.py doesn't define {entry.entry}()")
    ref = {n.name for n in ast.parse(entry.reference_code).body if isinstance(n, ast.FunctionDef)}
    if "reference" not in ref:
        raise LibraryError(f"{where}: reference.py doesn't define reference()")
    n_lines = len(entry.python_code.splitlines())
    try:
        templates = compile_templates(entry.narration)
        compile_visual(entry.visual)
    except (TemplateError, AnimationError) as exc:
        raise LibraryError(f"{where}: {exc}") from exc
    for t in templates:
        if not 1 <= t.line <= n_lines:
            raise LibraryError(f"{where}: template {t.index} refers to line {t.line}")
    cpp_n = len(entry.cpp_code.splitlines())
    for py, cpp in entry.cpp_line_map().items():
        if not (1 <= py <= n_lines and 1 <= cpp <= cpp_n):
            raise LibraryError(f"{where}: cpp_lines {py} -> {cpp} is out of range")
    if not entry.tests:
        raise LibraryError(f"{where}: no tests")
    try:
        schema = compile_schema(entry.schema)
    except SchemaError as exc:
        raise LibraryError(f"{where}: schema: {exc}") from exc
    for name, inp in [("default_input", entry.default_input)] + [
        (f"test {i}", t) for i, t in enumerate(entry.tests)
    ]:
        issues = validate(schema, inp.get("args"))
        if issues:
            raise LibraryError(f"{where}: {name} breaks the schema: {issues[0]}")
    if entry.validator_code and "validate" not in {
        n.name for n in ast.parse(entry.validator_code).body if isinstance(n, ast.FunctionDef)
    }:
        raise LibraryError(f"{where}: validator.py doesn't define validate()")


def load_all(root: Path) -> list[EntrySource]:
    if not root.is_dir():
        raise LibraryError(f"library directory not found: {root}")
    entries = [load_entry(d) for d in sorted(root.iterdir()) if (d / "entry.json").exists()]
    return sorted(entries, key=lambda e: (e.order, e.slug))


def seed(session: Session, entries: list[EntrySource]) -> None:
    """Upsert entries. A changed entry loses its verification until it's verified again."""
    existing = {e.slug: e for e in session.scalars(select(LibraryEntry))}
    for src in entries:
        content = asdict(src)
        for key in ("slug", "title", "category", "description"):
            content.pop(key)
        content["content_hash"] = src.content_hash
        row = existing.get(src.slug)
        if row is None:
            session.add(LibraryEntry(slug=src.slug, title=src.title, category=src.category,
                                     description=src.description, content=content,
                                     verification=None))  # fmt: skip
            continue
        if row.content.get("content_hash") != src.content_hash:
            row.verification = None
        row.title, row.category, row.description, row.content = (
            src.title,
            src.category,
            src.description,
            content,
        )
    for slug in set(existing) - {e.slug for e in entries}:
        session.delete(existing[slug])
    session.commit()
    log.info("library seeded: %d entries", len(entries))


def from_row(row: LibraryEntry) -> EntrySource:
    c = row.content
    return EntrySource(
        slug=row.slug, title=row.title, category=row.category, description=row.description,
        **{k: c[k] for k in ("summary", "order", "entry", "note", "default_input", "tests",
                             "cpp_lines", "visual", "narration", "python_code", "cpp_code",
                             "reference_code", "schema")},
        validator_code=c.get("validator_code", ""),
        result_kind=c.get("result_kind", ""),
    )  # fmt: skip
