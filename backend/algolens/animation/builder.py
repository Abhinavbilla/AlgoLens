"""Turn a recorded trace into what the player shows (plan §7.3).

Every frame of the output corresponds to exactly one recorded frame, in order; nothing is
interpolated. Panels (arrays, variables, maps) are resolved here from that frame's state,
so the browser only draws them. A visual spec chooses what to show and how, never values.
"""

from dataclasses import dataclass
from typing import Any

from algolens.animation.values import FrameView, display
from algolens.narration import expr
from algolens.narration.engine import NarrationTemplate, narrate
from algolens.narration.expr import ExprError, Node, evaluate

MAX_FRAMES = 300  # spec: an animation has at most 300 frames


class AnimationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # "too_long" (caller should pick a smaller input) or "bad_visual"


# --- visual spec -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pointer:
    label: str
    at: Node


@dataclass(frozen=True)
class Range:
    label: str
    start: Node
    end: Node  # exclusive


@dataclass(frozen=True)
class Panel:
    kind: str  # array | vars | map
    label: str
    var: Node | None = None
    var_source: str = ""
    names: tuple[str, ...] = ()
    pointers: tuple[Pointer, ...] = ()
    range: Range | None = None


def compile_visual(spec: dict) -> list[Panel]:
    panels = []
    for i, p in enumerate(spec.get("panels", [])):
        kind = p.get("kind")
        try:
            if kind in ("array", "map"):
                var = expr.parse(p["var"])
                if not expr.is_path(var):
                    raise AnimationError("bad_visual", f"panel {i}: `var` must be a variable path")
                pointers = tuple(Pointer(q["label"], expr.parse(q["at"]))
                                 for q in p.get("pointers", []))  # fmt: skip
                rng = p.get("range")
                rng = Range(rng["label"], expr.parse(rng["from"]), expr.parse(rng["to"])) \
                    if rng else None  # fmt: skip
                panels.append(Panel(kind, p.get("label", p["var"]), var, p["var"],
                                    pointers=pointers, range=rng))  # fmt: skip
            elif kind == "vars":
                names = tuple(p["vars"])
                for n in names:
                    if not n.isidentifier():
                        raise AnimationError("bad_visual", f"panel {i}: {n!r} is not a name")
                panels.append(Panel("vars", p.get("label", "Variables"), names=names))
            else:
                raise AnimationError("bad_visual", f"panel {i}: unknown kind {kind!r}")
        except (KeyError, TypeError, ExprError) as exc:
            raise AnimationError("bad_visual", f"panel {i}: {exc}") from exc
    return panels


# --- building ----------------------------------------------------------------------------------


def build(
    trace: dict,
    *,
    source: str,
    templates: list[NarrationTemplate],
    panels: list[Panel],
    cpp_lines: dict[int, int] | None = None,
) -> dict:
    if trace.get("truncated"):
        raise AnimationError("too_long", f"recording stopped early ({trace['truncated']})")
    frames, heap = trace["frames"], trace["heap"]
    if len(frames) > MAX_FRAMES:
        raise AnimationError("too_long", f"{len(frames)} steps; the limit is {MAX_FRAMES}")
    lines = source.splitlines()
    views = [FrameView(f, heap) for f in frames]
    out = []
    for i, view in enumerate(views):
        before = before_view(views[i - 1] if i else None, view)
        f = view.frame
        frame: dict[str, Any] = {
            "i": i,
            "line": f["line"],
            "next": f["next"],
            "cpp_line": nearest_cpp_line(cpp_lines or {}, f["line"]),
            "code": lines[f["line"] - 1].strip() if 0 < f["line"] <= len(lines) else "",
            "ops": i + 1,
            "aid": f["aid"],
            "stack": [_stack_entry(a, view, before) for a in f["stack"]],
            "panels": [_panel(p, view, before) for p in panels],
            "narration": narrate(templates, view, before),
        }
        if "ret" in f:
            frame["ret"] = display(view.plain(f["ret"]))
        if "raised" in f:
            frame["raised"] = f["raised"]
        out.append(frame)
    return {"frames": out, "total_ops": len(out)}


def before_view(prev: FrameView | None, cur: FrameView) -> FrameView | None:
    """The state just before `cur`'s line ran, seen from `cur`'s activation. None if that
    activation didn't exist yet (its first line), so nothing is marked as changed."""
    if prev is None or not prev.has_activation(cur.frame["aid"]):
        return None
    return FrameView(prev.frame, prev.heap, aid=cur.frame["aid"])


def nearest_cpp_line(mapping: dict[int, int], py_line: int) -> int | None:
    """The mapped C++ line, or that of the closest earlier mapped Python line."""
    if py_line in mapping:
        return mapping[py_line]
    earlier = [p for p in mapping if p < py_line]
    return mapping[max(earlier)] if earlier else None


def _stack_entry(act: dict, view: FrameView, before: FrameView | None) -> dict:
    args = ", ".join(
        f"{p}={display(view.plain(act['locals'][p]))}" for p in act.get("params", [])
        if p in act["locals"]
    )  # fmt: skip
    call = f"{act['fn']}({args})"
    return {
        "aid": act["aid"],
        "fn": act["fn"],
        "line": act["line"],
        "call": call if len(call) <= 80 else call[:79] + "…",
        "new": before is None or not before.has_activation(act["aid"]),
    }


def _value(node: Node, view: FrameView, before: FrameView | None):
    return view.plain(evaluate(node, view.env(before)))


def _panel(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    if p.kind == "vars":
        items = []
        for name in p.names:
            try:
                value = view.plain(view.lookup(name))
            except KeyError:
                items.append({"name": name, "defined": False})
                continue
            items.append({"name": name, "defined": True, "value": display(value),
                          "changed": _changed_var(name, value, before)})  # fmt: skip
        return {"kind": "vars", "label": p.label, "items": items}

    try:
        value = _value(p.var, view, before)
    except ExprError:
        return {"kind": p.kind, "label": p.label, "defined": False}
    old = None
    if before is not None:
        try:
            old = _value(p.var, before, None)
        except ExprError:
            old = None

    if p.kind == "map":
        if not isinstance(value, dict):
            return {"kind": "map", "label": p.label, "defined": False}
        entries = [{"key": display(k), "value": display(v),
                    "changed": before is not None and (not isinstance(old, dict)
                                                       or k not in old or old[k] != v)}
                   for k, v in value.items()]  # fmt: skip
        return {"kind": "map", "label": p.label, "defined": True, "entries": entries}

    if not isinstance(value, list | str | tuple):
        return {"kind": "array", "label": p.label, "defined": False}
    items = list(value)
    changed = []
    if before is not None and isinstance(old, list | str | tuple):
        old_items = list(old)
        changed = [i for i, x in enumerate(items) if i >= len(old_items) or old_items[i] != x]
    pointers = []
    for ptr in p.pointers:
        try:
            at = _value(ptr.at, view, before)
        except ExprError:
            continue
        if isinstance(at, int) and not isinstance(at, bool) and -1 <= at <= len(items):
            pointers.append({"label": ptr.label, "index": at})
    panel = {
        "kind": "array",
        "label": p.label,
        "defined": True,
        "items": [display(x, quote=False) for x in items],
        "changed": changed,
        "pointers": pointers,
    }
    if p.range:
        try:
            start, end = _value(p.range.start, view, before), _value(p.range.end, view, before)
            if isinstance(start, int) and isinstance(end, int):
                panel["range"] = {"label": p.range.label, "from": start, "to": end}
        except ExprError:
            pass
    return panel


def _changed_var(name: str, value: Any, before: FrameView | None) -> bool:
    if before is None:
        return False
    try:
        return before.plain(before.lookup(name)) != value
    except KeyError:
        return True  # newly defined
