"""Panels: what a visual spec draws for each frame, resolved from that frame's state.

A visual spec is {"panels": [...]}; each panel has a "kind", an optional "label", and
fields below. Fields marked (expr) are expressions in the narration language. Some see extra
names: `item` (an element of the collection), `node` (a graph node number), `row` / `col`.
Panels choose what to show and how; every value comes from the recorded state.

    array        var, item (expr: text per cell), pointers [{label, at}],
                 range {label, from, to} (to is exclusive: from=lo, to=hi + 1 covers lo..hi)
    stack        var, item          bottom to top (the end of the list is the top)
    queue        var, item          front first
    list         var, item          chips, for lists of results
    map          var
    vars         vars ["name", ...]
    linked_list  var (a name), pointers [{label, at (a name)}]
    tree         var (a name), pointers [{label, at (a name)}], marks
    graph        nodes (expr: count), edges (expr: list of [u, v] or [u, v, w]), directed,
                 node_label (expr, sees node), pointers [{label, at}], marks
    grid         var (2D list), text (expr, sees row/col), hide_when (expr), marks,
                 pointers [{label, row, col}], row_header / col_header {text (expr), offset}

marks: [{"label": ..., "from": <expr: a collection>, "item": <expr: what each element means>}
        or {"label": ..., "when": <expr: true for the node/cell>}]. For trees, "from" holds
        node objects; for graphs, node numbers (after "item"); for grids, (row, col) pairs.
"""

import math
from dataclasses import dataclass, field
from typing import Any

from algolens.animation.values import CYCLE, FrameView, Opaque, display
from algolens.narration import expr
from algolens.narration.expr import Env, ExprError, Node, evaluate

EXPR_KEYS = {"var", "item", "at", "from", "to", "text", "hide_when", "when", "nodes", "edges",
             "node_label", "row", "col"}  # fmt: skip
KINDS = {"array", "stack", "queue", "list", "map", "vars", "linked_list", "tree", "graph", "grid"}
NEEDS_VAR = {"array", "stack", "queue", "list", "map", "linked_list", "tree", "grid"}
NAME_ONLY = {"linked_list", "tree"}  # `var` and pointer `at` must be plain names (identity)
MAX_NODES = 200


class VisualError(ValueError):
    pass


@dataclass(frozen=True)
class Panel:
    kind: str
    label: str
    spec: dict = field(default_factory=dict)  # the panel's fields, expressions parsed

    def get(self, key: str, default: Any = None) -> Any:
        return self.spec.get(key, default)


def compile_visual(raw: dict) -> list[Panel]:
    panels = []
    for i, p in enumerate(raw.get("panels", [])):
        where = f"panel {i}"
        if not isinstance(p, dict) or p.get("kind") not in KINDS:
            raise VisualError(
                f"{where}: unknown kind {p.get('kind') if isinstance(p, dict) else p!r}"
            )
        kind = p["kind"]
        try:
            spec = _parse(p, where)
        except ExprError as exc:
            raise VisualError(f"{where}: {exc}") from exc
        if kind in NEEDS_VAR and "var" not in spec:
            raise VisualError(f"{where}: {kind} needs `var`")
        if kind in NEEDS_VAR and not expr.is_path(spec["var"]):
            raise VisualError(f"{where}: `var` must be a variable path")
        if kind in NAME_ONLY:
            names = [spec["var"]] + [q["at"] for q in spec.get("pointers", [])]
            if not all(isinstance(n, expr.Name) for n in names):
                raise VisualError(f"{where}: {kind} `var` and pointers must be plain names")
        if kind == "vars":
            names = p.get("vars")
            if not isinstance(names, list) or not all(
                isinstance(n, str) and n.isidentifier() for n in names
            ):
                raise VisualError(f"{where}: `vars` must be a list of names")
        if kind == "graph" and ("nodes" not in spec or "edges" not in spec):
            raise VisualError(f"{where}: graph needs `nodes` and `edges`")
        default_label = {"vars": "Variables"}.get(kind, p.get("var", kind))
        panels.append(Panel(kind, p.get("label", default_label), spec))
    return panels


def _parse(v: Any, where: str, key: str | None = None) -> Any:
    if isinstance(v, dict):
        return {k: _parse(x, where, k) for k, x in v.items()}
    if isinstance(v, list):
        return [_parse(x, where, key) for x in v]
    if key in EXPR_KEYS and isinstance(v, str):
        return expr.parse(v)
    return v


# --- rendering ---------------------------------------------------------------------------------


def render(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    base = {"kind": p.kind, "label": p.label}
    try:
        return {**base, **_RENDERERS[p.kind](p, view, before)}
    except (ExprError, KeyError):  # a variable this panel needs isn't defined at this step
        return {**base, "defined": False}


def _env(view: FrameView, before: FrameView | None, extra: dict | None = None) -> Env:
    extra = extra or {}
    return Env(
        now=lambda n: extra[n] if n in extra else view.lookup(n),
        before=before.lookup if before else None,
        deref=view.deref,
    )


def _eval(node: Node, view: FrameView, before=None, extra=None) -> Any:
    return view.plain(evaluate(node, _env(view, before, extra)))


def _encoded_items(node: Node, view: FrameView) -> list:
    """The collection's elements, still encoded (keeps object identity for trees/lists)."""
    v = view.deref(evaluate(node, _env(view, None)) if not expr.is_path(node) else _raw(node, view))
    if isinstance(v, dict):
        return list(v.keys())
    if not isinstance(v, list):
        raise ExprError("not a collection")
    return v


def _raw(node: Node, view: FrameView) -> Any:
    """Evaluate a path but keep the final value encoded."""
    if isinstance(node, expr.Name):
        try:
            return view.lookup(node.name)
        except KeyError:
            raise ExprError(f"unknown variable {node.name!r}") from None
    env = _env(view, None)
    if isinstance(node, expr.Index):
        container = view.deref(_raw(node.obj, view))
        key = evaluate(node.index, env)
        if isinstance(container, dict):
            return container.get(key, container.get(str(key)))
        return container[key]
    if isinstance(node, expr.Field):
        return view.deref(_raw(node.obj, view)).get(node.name)
    return evaluate(node, env)


def _text(v: Any) -> str:
    """Cell/item text: tree and list nodes show their value."""
    if isinstance(v, dict) and "val" in v and set(v) <= {"val", "left", "right", "next"}:
        return display(v["val"], quote=False)
    return display(v, quote=False)


def _same(view: FrameView, before: FrameView | None, node: Node) -> tuple[Any, Any]:
    now = _eval(node, view)
    if before is None:
        return now, None
    try:
        return now, _eval(node, before)
    except ExprError:
        return now, None


def _sequence(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    items = _encoded_items(p.get("var"), view)
    now, old = _same(view, before, p.get("var"))
    texts = []
    for enc in items:
        if p.get("item") is not None:
            texts.append(display(_eval(p.get("item"), view, extra={"item": enc}), quote=False))
        else:
            texts.append(_text(view.plain(enc)))
    changed = []
    if before is not None and isinstance(old, list | tuple | str):
        old = list(old)
        changed = [i for i, x in enumerate(list(now)) if i >= len(old) or old[i] != x]
    return {"defined": True, "items": texts, "changed": changed}


def _array(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    value = _eval(p.get("var"), view)
    if not isinstance(value, list | str | tuple):
        return {"defined": False}
    out = _sequence(p, view, before)
    items = out["items"]
    pointers = []
    for ptr in p.get("pointers", []):
        try:
            at = _eval(ptr["at"], view, before)
        except ExprError:
            continue
        if isinstance(at, int) and not isinstance(at, bool) and -1 <= at <= len(items):
            pointers.append({"label": ptr["label"], "index": at})
    out["pointers"] = pointers
    rng = p.get("range")
    if rng:
        try:
            start, end = _eval(rng["from"], view, before), _eval(rng["to"], view, before)
            if isinstance(start, int) and isinstance(end, int):
                out["range"] = {"label": rng["label"], "from": start, "to": end}
        except ExprError:
            pass
    return out


def _map(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    value, old = _same(view, before, p.get("var"))
    if not isinstance(value, dict):
        return {"defined": False}
    entries = [{"key": display(k), "value": display(v),
                "changed": before is not None and (not isinstance(old, dict) or k not in old
                                                   or old[k] != v)}
               for k, v in value.items()]  # fmt: skip
    return {"defined": True, "entries": entries}


def _vars(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    items = []
    for name in p.get("vars"):
        try:
            value = view.plain(view.lookup(name))
        except KeyError:
            items.append({"name": name, "defined": False})
            continue
        changed = False
        if before is not None:
            try:
                changed = before.plain(before.lookup(name)) != value
            except KeyError:
                changed = True
        items.append({"name": name, "defined": True, "value": display(value), "changed": changed})
    return {"items": items}


def _ref(v: Any) -> int | None:
    return v["ref"] if isinstance(v, dict) and "ref" in v else None


def _pointer_refs(p: Panel, view: FrameView) -> list[tuple[str, int | None]]:
    out = []
    for ptr in p.get("pointers", []):
        try:
            out.append((ptr["label"], _ref(view.lookup(ptr["at"].name))))
        except KeyError:
            continue
    return out


def _linked_list(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    head = view.lookup(p.get("var").name)
    nodes, seen, ref, cycle_to = [], {}, _ref(head), None
    while ref is not None and len(nodes) < MAX_NODES:
        if ref in seen:
            cycle_to = seen[ref]
            break
        seen[ref] = len(nodes)
        fields = view.content(ref)["fields"]
        nodes.append({"id": ref, "text": _text(view.plain(fields.get("val")))})
        ref = _ref(fields.get("next"))
    pointers = [{"label": label, "node": r} for label, r in _pointer_refs(p, view)]
    return {"defined": True, "nodes": nodes, "cycle_to": cycle_to, "pointers": pointers}


def _tree(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    root = _ref(view.lookup(p.get("var").name))
    nodes: list[dict] = []
    edges: list[dict] = []
    order: list[int] = []

    def walk(ref: int | None, depth: int, seen: set) -> None:  # in-order: x positions
        if ref is None or ref in seen or len(seen) >= MAX_NODES:
            return
        seen.add(ref)
        fields = view.content(ref)["fields"]
        left, right = _ref(fields.get("left")), _ref(fields.get("right"))
        walk(left, depth + 1, seen)
        order.append(ref)
        nodes.append({"id": ref, "text": _text(view.plain(fields.get("val"))), "depth": depth})
        for child in (left, right):
            if child is not None:
                edges.append({"from": ref, "to": child})
        walk(right, depth + 1, seen)

    walk(root, 0, set())
    x = {ref: i for i, ref in enumerate(order)}
    marks = _object_marks(p, view, [n["id"] for n in nodes])
    for n in nodes:
        n["x"], n["y"] = x[n["id"]], n.pop("depth")
        n["marks"] = marks.get(n["id"], [])
    pointers = [{"label": label, "node": r} for label, r in _pointer_refs(p, view)]
    return {
        "defined": True,
        "nodes": nodes,
        "edges": edges,
        "pointers": pointers,
        "width": len(nodes),
        "height": 1 + max((n["y"] for n in nodes), default=-1),
    }


def _object_marks(p: Panel, view: FrameView, refs: list[int]) -> dict[int, list[str]]:
    marks: dict[int, list[str]] = {}
    for m in p.get("marks", []):
        hit: set[int] = set()
        try:
            if "from" in m:
                hit = {
                    r for r in (_ref(x) for x in _encoded_items(m["from"], view)) if r is not None
                }
            elif "when" in m:
                hit = {
                    r for r in refs if _eval(m["when"], view, extra={"node": {"ref": r}}) is True
                }
        except ExprError:
            continue
        for r in refs:
            if r in hit:
                marks.setdefault(r, []).append(m["label"])
    return marks


def _graph(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    n = _eval(p.get("nodes"), view)
    if not isinstance(n, int) or not 0 <= n <= MAX_NODES:
        return {"defined": False}
    edges = []
    for e in _eval(p.get("edges"), view) or []:
        e = list(e) if isinstance(e, list | tuple) else []
        if len(e) >= 2 and all(isinstance(x, int) and 0 <= x < n for x in e[:2]):
            edges.append({"u": e[0], "v": e[1], "w": display(e[2]) if len(e) > 2 else None})
    marks: dict[int, list[str]] = {}
    for m in p.get("marks", []):
        try:
            if "from" in m:
                hit = set()
                for enc in _encoded_items(m["from"], view):
                    v = (
                        _eval(m["item"], view, extra={"item": enc})
                        if "item" in m
                        else view.plain(enc)
                    )
                    if isinstance(v, int):
                        hit.add(v)
            else:
                hit = {x for x in range(n) if _eval(m["when"], view, extra={"node": x}) is True}
        except ExprError:
            continue
        for x in sorted(hit):
            if 0 <= x < n:
                marks.setdefault(x, []).append(m["label"])
    nodes = []
    for x in range(n):  # fixed circle layout: nodes never move between steps
        angle = 2 * math.pi * x / max(n, 1) - math.pi / 2
        label = None
        if p.get("node_label") is not None:
            try:
                label = display(_eval(p.get("node_label"), view, extra={"node": x}), quote=False)
            except ExprError:
                label = None
        nodes.append({"id": x, "x": round(0.5 + 0.42 * math.cos(angle), 4),
                      "y": round(0.5 + 0.42 * math.sin(angle), 4), "label": label,
                      "marks": marks.get(x, [])})  # fmt: skip
    pointers = []
    for ptr in p.get("pointers", []):
        try:
            at = _eval(ptr["at"], view)
        except ExprError:
            continue
        if isinstance(at, int) and 0 <= at < n:
            pointers.append({"label": ptr["label"], "node": at})
    return {"defined": True, "nodes": nodes, "edges": edges, "pointers": pointers,
            "directed": bool(p.get("directed", False))}  # fmt: skip


def _grid(p: Panel, view: FrameView, before: FrameView | None) -> dict:
    grid, old = _same(view, before, p.get("var"))
    if not isinstance(grid, list) or not all(isinstance(r, list | str) for r in grid):
        return {"defined": False}
    cell_marks: dict[tuple[int, int], list[str]] = {}
    for m in p.get("marks", []):
        try:
            if "from" in m:
                for v in _eval(m["from"], view) or []:
                    if isinstance(v, list | tuple) and len(v) == 2:
                        cell_marks.setdefault((v[0], v[1]), []).append(m["label"])
            else:
                for r, row in enumerate(grid):
                    for c in range(len(row)):
                        if _eval(m["when"], view, extra={"row": r, "col": c}) is True:
                            cell_marks.setdefault((r, c), []).append(m["label"])
        except ExprError:
            continue
    rows = []
    for r, row in enumerate(grid):
        cells = []
        for c, value in enumerate(row):
            extra = {"row": r, "col": c}
            text = value
            if p.get("text") is not None:
                text = _eval(p.get("text"), view, extra=extra)
            if (
                p.get("hide_when") is not None
                and _eval(p.get("hide_when"), view, extra=extra) is True
            ):
                text = ""
            changed = (before is not None and isinstance(old, list) and r < len(old)
                       and c < len(old[r]) and old[r][c] != value)  # fmt: skip
            cells.append(
                {
                    "text": text if isinstance(text, str) else display(text, quote=False),
                    "marks": cell_marks.get((r, c), []),
                    "changed": bool(changed),
                }
            )
        rows.append(cells)
    pointers = []
    for ptr in p.get("pointers", []):
        try:
            r, c = _eval(ptr["row"], view), _eval(ptr["col"], view)
        except ExprError:
            continue
        if (
            isinstance(r, int)
            and isinstance(c, int)
            and 0 <= r < len(grid)
            and 0 <= c < len(grid[r])
        ):
            pointers.append({"label": ptr["label"], "row": r, "col": c})
    out = {"defined": True, "rows": rows, "pointers": pointers}
    for key in ("row_header", "col_header"):
        h = p.get(key)
        if h:
            try:
                labels = _eval(h["text"], view)
                labels = [display(x, quote=False) for x in labels]
                offset = h.get("offset", 0)
                count = len(rows) if key == "row_header" else max((len(r) for r in rows), default=0)
                out[key] = ["" if i < offset or i - offset >= len(labels) else labels[i - offset]
                            for i in range(count)]  # fmt: skip
            except ExprError:
                pass
    return out


_RENDERERS = {
    "array": _array,
    "stack": _sequence,
    "queue": _sequence,
    "list": _sequence,
    "map": _map,
    "vars": _vars,
    "linked_list": _linked_list,
    "tree": _tree,
    "graph": _graph,
    "grid": _grid,
}

__all__ = ["CYCLE", "Opaque", "Panel", "VisualError", "compile_visual", "render"]
