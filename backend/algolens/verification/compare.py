"""How two outputs are compared (plan §4 `comparator`).

exact             equal as JSON values
float             like exact, but numbers may differ by `tolerance` (default 1e-6),
                  absolute or relative
unordered         the top-level list's order doesn't matter
unordered_nested  neither the top-level list's order nor each inner list's order matters
                  (e.g. "return all triplets, in any order")
checker           judged by an AI-written check() in the sandbox (see pipeline/verify.py)
"""

import json
import math
from typing import Any

KINDS = ("exact", "float", "unordered", "unordered_nested", "checker")


def same(kind: str, a: Any, b: Any, tolerance: float = 1e-6) -> bool:
    if kind == "exact":
        return _exact(a, b)
    if kind == "float":
        return _close(a, b, tolerance)
    if kind == "unordered":
        return isinstance(a, list) and isinstance(b, list) and _sorted(a) == _sorted(b)
    if kind == "unordered_nested":
        if not (isinstance(a, list) and isinstance(b, list)):
            return False
        norm = lambda xs: _sorted([_sorted(x) if isinstance(x, list) else x for x in xs])  # noqa: E731
        return norm(a) == norm(b)
    raise ValueError(f"comparator {kind!r} can't be applied directly")


def _exact(a: Any, b: Any) -> bool:
    # bool is not a number here: True must not equal 1.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_exact(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_exact(a[k], b[k]) for k in a)
    return a == b


def _close(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, int | float) and isinstance(b, int | float):
        if math.isnan(a) or math.isnan(b):
            return False
        return abs(a - b) <= tol or abs(a - b) <= tol * max(abs(a), abs(b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], tol) for k in a)
    return a == b


def _sorted(xs: list) -> list:
    return sorted(xs, key=lambda x: json.dumps(x, sort_keys=True))
