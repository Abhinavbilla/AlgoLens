"""Read tracer values (encoding: sandbox/driver/tracer.py) as they were at one frame."""

from typing import Any

from algolens.narration.expr import Env

MAX_DISPLAY_ITEMS = 30
CYCLE = "…"


class FrameView:
    """One recorded frame plus the shared heap: everything needed to read its state."""

    def __init__(self, frame: dict, heap: dict[str, dict], aid: int | None = None):
        self.frame = frame
        self.heap = heap
        # Whose locals come first in lookups. Defaults to the activation that ran the line;
        # a "before" view uses the *current* frame's activation so old(x) means this call's x.
        self.aid = frame["aid"] if aid is None else aid

    # --- lookups -----------------------------------------------------------------------------

    def activations(self) -> list[dict]:
        return self.frame["stack"]

    def own(self) -> dict:
        return next(a for a in self.frame["stack"] if a["aid"] == self.aid)

    def has_activation(self, aid: int) -> bool:
        return any(a["aid"] == aid for a in self.frame["stack"])

    def lookup(self, name: str) -> Any:
        """Encoded value of `name`: the frame's own activation first, then the other active
        calls from innermost to outermost (so closure variables like `res` resolve)."""
        own = self.own()
        if name in own["locals"]:
            return own["locals"][name]
        for act in reversed(self.frame["stack"]):
            if name in act["locals"]:
                return act["locals"][name]
        raise KeyError(name)

    def content(self, number: int) -> dict:
        version = self.frame["objects"][str(number)]
        return self.heap[f"{number}.{version}"]

    # --- decoding ----------------------------------------------------------------------------

    def deref(self, v: Any) -> Any:
        """Decode one level, leaving nested values encoded (for the narration evaluator).
        The result is a ShallowList/ShallowDict, so it can't be mistaken for an encoded value
        later (a user's map could well have a key called "ref")."""
        if type(v) is not dict:  # already decoded (scalar, Shallow*), or not a value
            return v
        if "ref" in v:
            c = self.content(v["ref"])
            if c["type"] == "dict":
                return ShallowDict({self.key(k): x for k, x in c["items"]})
            if c["type"] == "object":
                return ShallowDict(c["fields"])
            return ShallowList(c["items"])
        if "tuple" in v:
            return ShallowList(v["tuple"])
        if "int" in v:
            return int(v["int"])
        if "float" in v:
            return float(v["float"])
        return v  # {"opaque": ...}: has no value the evaluator can use

    def key(self, k: Any) -> Any:
        """A map key, fully decoded and hashable."""
        if isinstance(k, dict):
            if "tuple" in k:
                return tuple(self.key(x) for x in k["tuple"])
            if "int" in k:
                return int(k["int"])
            if "float" in k:
                return float(k["float"])
            return repr(k)
        return k

    def plain(self, v: Any, _seen: frozenset = frozenset()) -> Any:
        """Fully decoded Python value. Cycles become CYCLE. Accepts encoded values and the
        partly decoded ones deref() returns (whose elements are still encoded)."""
        if isinstance(v, ShallowDict):
            return {k: self.plain(x, _seen) for k, x in v.items()}
        if isinstance(v, ShallowList):
            return [self.plain(x, _seen) for x in v]
        if type(v) is not dict:
            return v
        if "ref" in v:
            if v["ref"] in _seen:
                return CYCLE
            seen = _seen | {v["ref"]}
            c = self.content(v["ref"])
            if c["type"] == "dict":
                return {self.key(k): self.plain(x, seen) for k, x in c["items"]}
            if c["type"] == "object":
                return {k: self.plain(x, seen) for k, x in c["fields"].items()}
            return [self.plain(x, seen) for x in c["items"]]
        if "tuple" in v:
            return tuple(self.plain(x, _seen) for x in v["tuple"])
        if "int" in v:
            return int(v["int"])
        if "float" in v:
            return float(v["float"])
        if "opaque" in v:
            return Opaque(v["opaque"])
        return v

    def env(self, before: "FrameView | None") -> Env:
        return Env(
            now=self.lookup,
            before=before.lookup if before else None,
            deref=self.deref,
        )


class ShallowList(list):
    """A list decoded one level: its elements are still encoded."""


class ShallowDict(dict):
    """A map or object decoded one level: its values are still encoded."""


class Opaque:
    """A value the tracer couldn't represent (a function, a module, ...)."""

    def __init__(self, type_name: str):
        self.type_name = type_name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Opaque) and other.type_name == self.type_name

    def __hash__(self) -> int:
        return hash(self.type_name)

    def __repr__(self) -> str:
        return f"<{self.type_name}>"


def display(v: Any, *, quote: bool = True) -> str:
    """How a decoded value is written in panels and narration."""
    if v is None or isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return repr(v) if quote else v
    if isinstance(v, Opaque):
        return repr(v)
    if isinstance(v, tuple):
        inner = ", ".join(display(x) for x in v[:MAX_DISPLAY_ITEMS])
        return f"({inner}{',' if len(v) == 1 else ''})"
    if isinstance(v, list):
        more = ", …" if len(v) > MAX_DISPLAY_ITEMS else ""
        return "[" + ", ".join(display(x) for x in v[:MAX_DISPLAY_ITEMS]) + more + "]"
    if isinstance(v, dict):
        items = list(v.items())[:MAX_DISPLAY_ITEMS]
        more = ", …" if len(v) > MAX_DISPLAY_ITEMS else ""
        return "{" + ", ".join(f"{display(k)}: {display(x)}" for k, x in items) + more + "}"
    return str(v)


def numbers_in(v: Any, out: set[str]) -> None:
    """Every number in a decoded value, written as display() writes it."""
    if isinstance(v, bool) or v is None:
        return
    if isinstance(v, int | float):
        out.add(display(v))
    elif isinstance(v, list | tuple):
        for x in v:
            numbers_in(x, out)
    elif isinstance(v, dict):
        for k, x in v.items():
            numbers_in(k, out)
            numbers_in(x, out)
