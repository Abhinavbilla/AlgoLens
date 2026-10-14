"""Check an input against a schema, with messages a learner can act on.

`validate(schema, args)` takes the arguments in parameter order (the shape the sandbox
runs) and returns a list of Issues; empty means valid. The first problem found inside a
value is reported, not every one, so messages stay readable.
"""

import math
from dataclasses import dataclass
from typing import Any

from algolens.narration.expr import Env, ExprError, evaluate
from algolens.schema.model import (
    ArrayT,
    BoolT,
    EdgesT,
    FloatT,
    GridT,
    IntT,
    LinkedListT,
    MatrixT,
    OpsT,
    Range,
    Schema,
    StringT,
    TreeT,
    TypeSpec,
    resolve,
)

MAX_ISSUES = 20


@dataclass(frozen=True)
class Issue:
    path: str  # "nums", "nums[3]", "edges[2][0]", or "" for the input as a whole
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


class _Stop(Exception):
    def __init__(self, issue: Issue):
        self.issue = issue


def validate(schema: Schema, args: Any) -> list[Issue]:
    if not isinstance(args, list):
        return [Issue("", "the input must be a list of arguments")]
    if len(args) != len(schema.params):
        names = ", ".join(schema.names)
        return [Issue("", f"expected {len(schema.params)} arguments ({names}), got {len(args)}")]
    issues: list[Issue] = []
    values: dict[str, Any] = {}
    for param, value in zip(schema.params, args, strict=True):
        try:
            _check(param.type, value, param.name, values)
        except _Stop as stop:
            issues.append(stop.issue)
        except ValueError as exc:  # a bound couldn't be evaluated: an earlier param is wrong
            issues.append(Issue(param.name, f"can't be checked yet: {exc}"))
        values[param.name] = value
        if len(issues) >= MAX_ISSUES:
            return issues
    if issues:
        return issues  # constraints across params only make sense once each param is valid
    for c in schema.constraints:
        try:
            ok = evaluate(c.check, Env(now=values.__getitem__))
        except ExprError as exc:
            issues.append(Issue("", f"{c.message} (couldn't check: {exc})"))
            continue
        if ok is not True:
            issues.append(Issue("", c.message))
    return issues


def _fail(path: str, message: str) -> None:
    raise _Stop(Issue(path, message))


def _check(t: TypeSpec, v: Any, path: str, env: dict) -> None:
    match t:
        case IntT():
            if not isinstance(v, int) or isinstance(v, bool):
                _fail(path, f"must be a whole number (got {_show(v)})")
            _in_range(v, resolve(t.min, env), resolve(t.max, env), path)
        case FloatT():
            if not isinstance(v, int | float) or isinstance(v, bool) or not math.isfinite(v):
                _fail(path, f"must be a number (got {_show(v)})")
            _in_range(v, resolve(t.min, env), resolve(t.max, env), path)
        case BoolT():
            if not isinstance(v, bool):
                _fail(path, f"must be true or false (got {_show(v)})")
        case StringT():
            if not isinstance(v, str):
                _fail(path, f"must be text (got {_show(v)})")
            _length(len(v), t.len, path, env, "characters")
            bad = sorted(set(v) - set(t.chars))
            if bad:
                _fail(path, f"may only contain {_describe_chars(t)} (found {bad[0]!r})")
            if t.valid_parentheses and not _balanced(v):
                _fail(path, "must be a balanced string of parentheses")
        case ArrayT():
            _array(t, v, path, env)
        case MatrixT():
            rows = _list(v, path)
            _length(len(rows), t.rows, path, env, "rows")
            cols = None
            for i, row in enumerate(rows):
                row = _list(row, f"{path}[{i}]")
                if cols is None:
                    cols = len(row)
                    _length(cols, t.cols, f"{path}[{i}]", env, "columns")
                elif len(row) != cols:
                    _fail(
                        f"{path}[{i}]",
                        f"every row must have {cols} values (this one has {len(row)})",
                    )
                for j, x in enumerate(row):
                    _check(t.of, x, f"{path}[{i}][{j}]", env)
        case GridT():
            rows = _list(v, path)
            _length(len(rows), t.rows, path, env, "rows")
            width = None
            for i, row in enumerate(rows):
                row = _list(row, f"{path}[{i}]")
                width = len(row) if width is None else width
                if len(row) != width:
                    _fail(f"{path}[{i}]", f"every row must have {width} cells")
                if i == 0:
                    _length(width, t.cols, f"{path}[{i}]", env, "columns")
                for j, cell in enumerate(row):
                    if not isinstance(cell, str) or len(cell) != 1 or cell not in t.chars:
                        allowed = " ".join(repr(c) for c in t.chars)
                        _fail(f"{path}[{i}][{j}]", f"must be one of {allowed} (got {_show(cell)})")
        case LinkedListT():
            items = _list(v, path)
            _length(len(items), t.len, path, env, "nodes")
            for i, x in enumerate(items):
                _check(t.of, x, f"{path}[{i}]", env)
        case TreeT():
            _tree(t, v, path, env)
        case EdgesT():
            _edges(t, v, path, env)
        case OpsT():
            ops = _list(v, path)
            _length(len(ops), t.len, path, env, "operations")
            by_name = {o.name: o for o in t.ops}
            for i, op in enumerate(ops):
                op = _list(op, f"{path}[{i}]")
                if not op or op[0] not in by_name:
                    _fail(f"{path}[{i}]", f"must start with one of {', '.join(by_name)}")
                spec = by_name[op[0]]
                if len(op) - 1 != len(spec.args):
                    _fail(f"{path}[{i}]", f"{spec.name} takes {len(spec.args)} argument(s)")
                for j, (a, x) in enumerate(zip(spec.args, op[1:], strict=True)):
                    _check(a, x, f"{path}[{i}][{j + 1}]", env)


def _array(t: ArrayT, v: Any, path: str, env: dict) -> None:
    items = _list(v, path)
    _length(len(items), t.len, path, env, "values")
    for i, x in enumerate(items):
        _check(t.of, x, f"{path}[{i}]", env)
    if t.permutation_start is not None:
        expected = list(range(t.permutation_start, t.permutation_start + len(items)))
        if sorted(items) != expected:
            hi = t.permutation_start + len(items) - 1
            _fail(path, f"must contain each of {t.permutation_start}..{hi} exactly once")
    if t.distinct:
        seen: dict[Any, int] = {}
        for i, x in enumerate(items):
            if x in seen:
                _fail(
                    f"{path}[{i}]",
                    f"repeats {_show(x)} (already at {path}[{seen[x]}]); values must be distinct",
                )
            seen[x] = i
    if t.sorted:
        for i in range(1, len(items)):
            a, b = items[i - 1], items[i]
            if (t.sorted == "asc" and a > b) or (t.sorted == "desc" and a < b):
                order = "ascending" if t.sorted == "asc" else "descending"
                _fail(
                    path,
                    f"must be sorted in {order} order "
                    f"({path}[{i}] = {_show(b)} comes after {_show(a)})",
                )


def _tree(t: TreeT, v: Any, path: str, env: dict) -> None:
    items = _list(v, path)
    if items and items[0] is None:
        _fail(f"{path}[0]", "the root can't be null; use [] for an empty tree")
    if items and items[-1] is None:
        _fail(path, "drop the trailing nulls at the end")
    # Level order: each non-null node owns the next two slots as its children.
    nodes, slots, i = 0, 1, 0
    for i, x in enumerate(items):
        if i >= slots:
            _fail(f"{path}[{i}]", "has no parent; there are more values than open child slots")
        if x is not None:
            _check(t.of, x, f"{path}[{i}]", env)
            nodes += 1
            slots += 2
    _length(nodes, t.nodes, path, env, "nodes")
    if t.bst:
        order = _in_order(items)
        for a, b in zip(order, order[1:], strict=False):
            if a >= b:
                _fail(path, f"isn't a binary search tree: {b} comes after {a} in order")


def _in_order(items: list) -> list:
    children: dict[int, list[int | None]] = {}
    nxt = 1
    for i, x in enumerate(items):
        if x is None:
            continue
        kids = []
        for _ in range(2):
            kids.append(nxt if nxt < len(items) and items[nxt] is not None else None)
            nxt += 1
        children[i] = kids
    out: list = []

    def walk(i: int | None) -> None:
        if i is None:
            return
        walk(children[i][0])
        out.append(items[i])
        walk(children[i][1])

    if items:
        walk(0)
    return out


def _edges(t: EdgesT, v: Any, path: str, env: dict) -> None:
    edges = _list(v, path)
    n = resolve(t.nodes, env)
    _length(len(edges), t.count, path, env, "edges")
    width = 3 if t.weighted else 2
    seen = set()
    for i, e in enumerate(edges):
        e = _list(e, f"{path}[{i}]")
        if len(e) != width:
            shape = "[u, v, weight]" if t.weighted else "[u, v]"
            _fail(f"{path}[{i}]", f"each edge must be {shape}")
        for j in range(2):
            x = e[j]
            if not isinstance(x, int) or isinstance(x, bool) or not 0 <= x < n:
                _fail(
                    f"{path}[{i}][{j}]", f"must be a node number from 0 to {n - 1} (got {_show(x)})"
                )
        if t.weighted:
            _check(t.weight, e[2], f"{path}[{i}][2]", env)
        u, w = e[0], e[1]
        if u == w and not t.self_loops:
            _fail(f"{path}[{i}]", f"connects node {u} to itself; self-loops aren't allowed")
        key = (u, w) if t.directed else (min(u, w), max(u, w))
        if key in seen and not t.duplicates:
            _fail(f"{path}[{i}]", f"repeats the edge between {u} and {w}")
        seen.add(key)
    pairs = [(e[0], e[1]) for e in edges]
    if (t.connected or t.tree) and n > 0 and not _connected(n, pairs):
        _fail(path, "the graph must be connected")
    if t.tree and len(edges) != n - 1:
        _fail(path, f"a tree on {n} nodes has exactly {max(n - 1, 0)} edges (got {len(edges)})")
    if t.dag and _has_cycle(n, pairs):
        _fail(path, "must not contain a cycle")


def _connected(n: int, pairs: list) -> bool:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in pairs:
        parent[find(u)] = find(v)
    return len({find(x) for x in range(n)}) == 1


def _has_cycle(n: int, pairs: list) -> bool:
    indeg = [0] * n
    out: list[list[int]] = [[] for _ in range(n)]
    for u, v in pairs:
        out[u].append(v)
        indeg[v] += 1
    queue = [x for x in range(n) if indeg[x] == 0]
    done = 0
    while queue:
        x = queue.pop()
        done += 1
        for y in out[x]:
            indeg[y] -= 1
            if indeg[y] == 0:
                queue.append(y)
    return done != n


def _list(v: Any, path: str) -> list:
    if not isinstance(v, list):
        _fail(path, f"must be a list (got {_show(v)})")
    return v


def _length(n: int, r: Range, path: str, env: dict, unit: str) -> None:
    lo, hi = resolve(r.min, env), resolve(r.max, env)
    if n < lo:
        _fail(path, f"must have at least {lo} {unit} (got {n})")
    if n > hi:
        _fail(path, f"must have at most {hi} {unit} (got {n})")


def _in_range(v: float, lo: int, hi: int, path: str) -> None:
    if v < lo:
        _fail(path, f"must be at least {lo} (got {_show(v)})")
    if v > hi:
        _fail(path, f"must be at most {hi} (got {_show(v)})")


def _balanced(s: str) -> bool:
    depth = 0
    for ch in s:
        depth += 1 if ch == "(" else -1
        if depth < 0:
            return False
    return depth == 0


def _describe_chars(t: StringT) -> str:
    names = {"lowercase": "lowercase letters", "uppercase": "uppercase letters",
             "letters": "letters", "digits": "digits", "alnum": "letters and digits",
             "binary": "0 and 1", "parens": "( and )"}  # fmt: skip
    return names.get(t.chars_name, "the characters " + " ".join(repr(c) for c in t.chars))


def _show(v: Any) -> str:
    text = (
        repr(v) if not isinstance(v, bool | type(None)) else str(v).lower().replace("none", "null")
    )
    return text if len(text) <= 40 else text[:37] + "..."
