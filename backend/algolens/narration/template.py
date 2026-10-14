"""Narration template text: literal text plus `{expression}` placeholders (plan §7.4).

Parsed by this scanner, never by str.format (which would allow attribute and index access
on live objects). `{{` and `}}` are literal braces.

What a placeholder may contain in displayed text:
- a state path: `{r}`, `{nums[l]}`, `{node.val}`, `{old(r)}`
- a computed value over state paths: `{nums[l] + nums[r]}`, `{len(stack)}`. The renderer
  always shows these with their operands ("2 + 15 = 17").
- small constants from -2 to 2 as operands, shown with the working: `{j + 1}` renders as
  "2 + 1 = 3". A computed placeholder must still use at least one value from the state.
Not allowed in text: comparisons, and/or/not, string or boolean literals, other numeric
literals as operands, and any number written in the sentence itself (the grounding check
rejects it). Numeric literals are fine as indices: `{nums[0]}`. Conditions (`when`) may use
the full expression language.
"""

from dataclasses import dataclass

from algolens.narration import expr
from algolens.narration.expr import (
    BinOp,
    BoolOp,
    Compare,
    Index,
    Len,
    Lit,
    Neg,
    Node,
    Not,
    ParseError,
)

SMALL_LITERALS = range(-2, 3)  # constants allowed as operands, e.g. {j + 1}
MAX_TEMPLATE_LENGTH = 500
MAX_PLACEHOLDERS = 10


@dataclass(frozen=True)
class Placeholder:
    source: str
    node: Node

    @property
    def computed(self) -> bool:
        return not expr.is_path(self.node)


@dataclass(frozen=True)
class Template:
    segments: tuple[str | Placeholder, ...]

    @property
    def placeholders(self) -> list[Placeholder]:
        return [s for s in self.segments if isinstance(s, Placeholder)]


def parse_template(text: str) -> Template:
    if not isinstance(text, str):
        raise ParseError("template must be a string")
    if len(text) > MAX_TEMPLATE_LENGTH:
        raise ParseError(f"template longer than {MAX_TEMPLATE_LENGTH} characters")
    segments: list[str | Placeholder] = []
    literal: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "{" and text.startswith("{{", i):
            literal.append("{")
            i += 2
        elif ch == "}" and text.startswith("}}", i):
            literal.append("}")
            i += 2
        elif ch == "}":
            raise ParseError(f"unmatched '}}' at {i}")
        elif ch == "{":
            end = _placeholder_end(text, i + 1)
            source = text[i + 1 : end].strip()
            if literal:
                segments.append("".join(literal))
                literal = []
            segments.append(Placeholder(source, _parse_display(source)))
            i = end + 1
        else:
            literal.append(ch)
            i += 1
    if literal:
        segments.append("".join(literal))
    template = Template(tuple(segments))
    if len(template.placeholders) > MAX_PLACEHOLDERS:
        raise ParseError(f"more than {MAX_PLACEHOLDERS} placeholders")
    return template


def parse_condition(source: str) -> Node:
    """A `when` condition: the full expression language."""
    return expr.parse(source)


def _placeholder_end(text: str, start: int) -> int:
    quote = None
    i = start
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "{":
            raise ParseError(f"nested '{{' inside a placeholder at {i}")
        elif ch == "}":
            return i
        i += 1
    raise ParseError(f"unclosed '{{' at {start - 1}")


def _parse_display(source: str) -> Node:
    node = expr.parse(source)
    _check_display(node)
    if not expr.is_path(node) and not _uses_state(node):
        raise ParseError("a computed placeholder must use at least one value from the state")
    return node


def is_small_literal(node: Node) -> bool:
    """A small integer constant (SMALL_LITERALS), allowed as an operand in a placeholder."""
    if isinstance(node, Neg):
        return is_small_literal(node.operand)
    return (isinstance(node, Lit) and isinstance(node.value, int)
            and not isinstance(node.value, bool) and node.value in SMALL_LITERALS)  # fmt: skip


def _uses_state(node: Node) -> bool:
    if expr.is_path(node) or isinstance(node, Len):
        return True
    if isinstance(node, BinOp):
        return _uses_state(node.left) or _uses_state(node.right)
    if isinstance(node, Neg):
        return _uses_state(node.operand)
    return False


def _check_display(node: Node) -> None:
    if expr.is_path(node):
        _check_indices(node)
        return
    match node:
        case BinOp(_, left, right):
            for side in (left, right):
                if isinstance(side, Lit) or (
                    isinstance(side, Neg) and isinstance(side.operand, Lit)
                ):
                    if not is_small_literal(side):
                        raise ParseError(
                            "only small constants (-2 to 2) may appear in a placeholder; other "
                            "numbers in narration must come from the state"
                        )
                    continue
                _check_display(side)
        case Neg(operand):
            _check_display(operand)
        case Len(operand):
            if not expr.is_path(operand):
                raise ParseError("len() in text takes a state path")
            _check_indices(operand)
        case Compare() | BoolOp() | Not():
            raise ParseError("comparisons and and/or/not belong in `when`, not in text")
        case Lit():
            raise ParseError("literal values don't belong in a placeholder")
        case _:
            raise ParseError(f"not allowed in text: {type(node).__name__}")


def _check_indices(path: Node) -> None:
    # Indices inside a path may be literals (nums[0]) or any arithmetic over the state.
    while isinstance(path, Index | expr.Field | expr.Old):
        if isinstance(path, Index) and not isinstance(path.index, Lit):
            _check_index_expr(path.index)
        path = path.path if isinstance(path, expr.Old) else path.obj


def _check_index_expr(node: Node) -> None:
    if isinstance(node, Compare | BoolOp | Not):
        raise ParseError("comparisons and and/or/not are not valid indices")
