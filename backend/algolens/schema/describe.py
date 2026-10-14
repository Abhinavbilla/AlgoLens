"""Plain-language descriptions of input types, for hints next to the input editor."""

from algolens.schema.model import (
    ArrayT,
    BoolT,
    Bound,
    EdgesT,
    FloatT,
    GridT,
    IntT,
    LinkedListT,
    MatrixT,
    OpsT,
    Range,
    StringT,
    TreeT,
    TypeSpec,
)

_SOURCE_NAMES = {"lowercase": "lowercase letters", "uppercase": "uppercase letters",
                 "letters": "letters", "digits": "digits", "alnum": "letters and digits",
                 "binary": "0s and 1s", "parens": "( and )"}  # fmt: skip


def describe(t: TypeSpec) -> str:
    match t:
        case IntT():
            return f"a whole number from {_b(t.min)} to {_b(t.max)}"
        case FloatT():
            return f"a number from {_b(t.min)} to {_b(t.max)}"
        case BoolT():
            return "true or false"
        case StringT():
            chars = _SOURCE_NAMES.get(t.chars_name, "the characters " + "".join(t.chars))
            extra = ", balanced" if t.valid_parentheses else ""
            return f"text of {_r(t.len)} characters, using {chars}{extra}"
        case ArrayT():
            parts = []
            if t.sorted:
                parts.append("sorted" if t.sorted == "asc" else "sorted largest first")
            if t.distinct:
                parts.append("with no repeats")
            if t.permutation_start is not None:
                s = t.permutation_start
                return f"a list of {_r(t.len)} values that is a shuffle of {s}, {s + 1}, ..."
            lead = " ".join(parts[:1]) + " " if parts[:1] else ""
            tail = f" ({parts[1]})" if len(parts) > 1 else ""
            return f"a {lead}list of {_r(t.len)} values{tail}, each {_item(t.of)}"
        case MatrixT():
            return (
                f"a grid of numbers, {_r(t.rows)} rows by {_r(t.cols)} columns, each {_item(t.of)}"
            )
        case GridT():
            chars = " ".join(repr(c) for c in t.chars)
            return f"a grid of {_r(t.rows)} rows by {_r(t.cols)} columns of cells {chars}"
        case LinkedListT():
            return f"a linked list of {_r(t.len)} nodes, written as a list, each {_item(t.of)}"
        case TreeT():
            kind = "binary search tree" if t.bst else "binary tree"
            return f"a {kind} of {_r(t.nodes)} nodes, written level by level with null for gaps"
        case EdgesT():
            arrow = "directed " if t.directed else ""
            shape = "[u, v, weight]" if t.weighted else "[u, v]"
            props = [
                p
                for p, on in (("connected", t.connected), ("acyclic", t.dag), ("a tree", t.tree))
                if on
            ]
            extra = f"; the graph is {', '.join(props)}" if props else ""
            nodes = f"nodes 0 to {_b(t.nodes)} - 1"
            return f"a list of {_r(t.count)} {arrow}edges {shape} between {nodes}{extra}"
        case OpsT():
            names = ", ".join(o.name for o in t.ops)
            each = f"each [name, arguments...] with name one of {names}"
            return f"a list of {_r(t.len)} operations, {each}"
    return "a value"


def _b(b: Bound) -> str:
    if isinstance(b, int):
        if abs(b) >= 10**6 and str(abs(b)).rstrip("0") == "1":
            exp = len(str(abs(b))) - 1
            return f"{'-' if b < 0 else ''}10^{exp}"
        return str(b)
    return "the value of " + _src(b)


def _r(r: Range) -> str:
    lo, hi = r.source
    if lo == hi:
        return str(lo)
    return f"{lo if lo is not None else 0} to {hi}"


def _src(node) -> str:
    from algolens.narration.expr import Name

    return node.name if isinstance(node, Name) else "an earlier input"


def _item(t: TypeSpec) -> str:
    """describe(t) without its leading article, to follow "each"."""
    text = describe(t)
    for article in ("a ", "an "):
        if text.startswith(article):
            return text[len(article) :]
    return text
