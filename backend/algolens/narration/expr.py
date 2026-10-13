"""Restricted expression language for narration templates (plan §7.5). No eval/exec.

Narration runs in the worker, outside the sandbox, so template expressions are parsed by
this small grammar and evaluated over JSON snapshot data only (plain lists, dicts, numbers,
strings). There is no Python object to reach, no attribute access beyond four node fields,
no calls except len() and old(), no ** or slicing, and hard limits on size and magnitude.

Grammar (lowest to highest precedence):
    expr     := or
    or       := and ('or' and)*
    and      := not ('and' not)*
    not      := 'not' not | compare
    compare  := arith (('=='|'!='|'<'|'<='|'>'|'>=') arith)*       chainable
    arith    := term (('+'|'-') term)*
    term     := unary (('*'|'//'|'%') unary)*
    unary    := '-' unary | postfix
    postfix  := atom ('[' expr ']' | '.' FIELD)*
    atom     := INT | FLOAT | STRING | True | False | None | NAME
              | 'len' '(' expr ')' | 'old' '(' path ')' | '(' expr ')'
    path     := NAME ('[' expr ']' | '.' FIELD)*
    FIELD    := val | next | left | right

old(path) evaluates the whole path, including any indices inside it, in the state from
before the line ran.
"""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

MAX_LENGTH = 200
MAX_DEPTH = 32
MAX_INT_DIGITS = 19
MAX_MAGNITUDE = 10**18
NODE_FIELDS = frozenset({"val", "next", "left", "right"})
KEYWORDS = frozenset({"and", "or", "not", "True", "False", "None", "len", "old"})


class ExprError(Exception):
    """Base for every failure. Callers treat any ExprError as "template doesn't match"."""


class ParseError(ExprError):
    pass


class EvalError(ExprError):
    pass


# --- AST ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Lit:
    value: Any


@dataclass(frozen=True)
class Name:
    name: str


@dataclass(frozen=True)
class Index:
    obj: "Node"
    index: "Node"


@dataclass(frozen=True)
class Field:
    obj: "Node"
    name: str


@dataclass(frozen=True)
class Neg:
    operand: "Node"


@dataclass(frozen=True)
class BinOp:
    op: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Compare:
    first: "Node"
    rest: tuple[tuple[str, "Node"], ...]


@dataclass(frozen=True)
class BoolOp:
    op: str
    operands: tuple["Node", ...]


@dataclass(frozen=True)
class Not:
    operand: "Node"


@dataclass(frozen=True)
class Len:
    operand: "Node"


@dataclass(frozen=True)
class Old:
    path: "Node"


Node = Lit | Name | Index | Field | Neg | BinOp | Compare | BoolOp | Not | Len | Old


def is_path(node: Node) -> bool:
    """A reference into the state: a name, optionally indexed or field-accessed, or old(path)."""
    if isinstance(node, Name | Old):
        return True
    if isinstance(node, Index | Field):
        return is_path(node.obj)
    return False


# --- tokenizer ------------------------------------------------------------------------------

_TOKEN = re.compile(
    r"""
    (?P<ws>[ \t]+)
  | (?P<float>\d+\.\d+)
  | (?P<int>\d+)
  | (?P<string>'(?:[^'\\\n]|\\['"\\n])*'|"(?:[^"\\\n]|\\['"\\n])*")
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>//|==|!=|<=|>=|[-+*%<>()\[\].,])
    """,
    re.VERBOSE | re.ASCII,
)
_ESCAPES = {"\\'": "'", '\\"': '"', "\\\\": "\\", "\\n": "\n"}


@dataclass(frozen=True)
class _Tok:
    kind: str
    text: str
    pos: int


def _tokenize(src: str) -> list[_Tok]:
    tokens, pos = [], 0
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise ParseError(f"unexpected character {src[pos]!r} at {pos}")
        kind = m.lastgroup
        text = m.group()
        if kind == "name" and "__" in text:
            raise ParseError(f"names containing '__' are not allowed: {text!r}")
        if kind == "int" and (len(text) > MAX_INT_DIGITS or int(text) > MAX_MAGNITUDE):
            raise ParseError("integer literal too large")
        if kind == "float" and (len(text) > 40 or float(text) > MAX_MAGNITUDE):
            raise ParseError("number literal too large")
        if kind != "ws":
            tokens.append(_Tok(kind, text, pos))
        pos = m.end()
    return tokens


# --- parser ---------------------------------------------------------------------------------


@dataclass
class _Parser:
    tokens: list[_Tok]
    pos: int = 0
    depth: int = 0
    in_old: bool = field(default=False)

    def peek(self, text: str | None = None) -> _Tok | None:
        tok = self.tokens[self.pos] if self.pos < len(self.tokens) else None
        if text is not None and (tok is None or tok.text != text or tok.kind == "string"):
            return None
        return tok

    def take(self, text: str | None = None) -> _Tok:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end of expression")
        if text is not None and (tok.text != text or tok.kind == "string"):
            raise ParseError(f"expected {text!r} at {tok.pos}, found {tok.text!r}")
        self.pos += 1
        return tok

    def enter(self) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParseError("expression nested too deeply")

    def expr(self) -> Node:
        self.enter()
        try:
            return self.or_()
        finally:
            self.depth -= 1

    def or_(self) -> Node:
        operands = [self.and_()]
        while self.peek("or"):
            self.take()
            operands.append(self.and_())
        return operands[0] if len(operands) == 1 else BoolOp("or", tuple(operands))

    def and_(self) -> Node:
        operands = [self.not_()]
        while self.peek("and"):
            self.take()
            operands.append(self.not_())
        return operands[0] if len(operands) == 1 else BoolOp("and", tuple(operands))

    def not_(self) -> Node:
        if self.peek("not"):
            self.take()
            self.enter()
            try:
                return Not(self.not_())
            finally:
                self.depth -= 1
        return self.compare()

    def compare(self) -> Node:
        first = self.arith()
        rest = []
        while (tok := self.peek()) and tok.kind == "op" and tok.text in _COMPARE_OPS:
            self.take()
            rest.append((tok.text, self.arith()))
        return Compare(first, tuple(rest)) if rest else first

    def arith(self) -> Node:
        node = self.term()
        while (tok := self.peek()) and tok.kind == "op" and tok.text in ("+", "-"):
            self.take()
            node = BinOp(tok.text, node, self.term())
        return node

    def term(self) -> Node:
        node = self.unary()
        while (tok := self.peek()) and tok.kind == "op" and tok.text in ("*", "//", "%"):
            self.take()
            node = BinOp(tok.text, node, self.unary())
        return node

    def unary(self) -> Node:
        if self.peek("-"):
            self.take()
            self.enter()
            try:
                return Neg(self.unary())
            finally:
                self.depth -= 1
        return self.postfix(self.atom())

    def postfix(self, node: Node) -> Node:
        while True:
            if self.peek("["):
                self.take()
                node = Index(node, self.expr())
                self.take("]")
            elif self.peek("."):
                self.take()
                name = self.take()
                if name.kind != "name" or name.text not in NODE_FIELDS:
                    raise ParseError(f"only .val/.next/.left/.right are allowed, not {name.text!r}")
                node = Field(node, name.text)
            else:
                return node

    def atom(self) -> Node:
        tok = self.take()
        if tok.kind == "int":
            return Lit(int(tok.text))
        if tok.kind == "float":
            return Lit(float(tok.text))
        if tok.kind == "string":
            body = tok.text[1:-1]
            return Lit(re.sub(r"\\['\"\\n]", lambda m: _ESCAPES[m.group()], body))
        if tok.kind == "op" and tok.text == "(":
            node = self.expr()
            self.take(")")
            return node
        if tok.kind == "name":
            if tok.text in ("True", "False", "None"):
                return Lit({"True": True, "False": False, "None": None}[tok.text])
            if tok.text == "len":
                self.take("(")
                node = Len(self.expr())
                self.take(")")
                return node
            if tok.text == "old":
                if self.in_old:
                    raise ParseError("old() cannot be nested")
                self.take("(")
                self.in_old = True
                try:
                    path = self.postfix(self._name())
                finally:
                    self.in_old = False
                self.take(")")
                return Old(path)
            if tok.text in KEYWORDS:
                raise ParseError(f"unexpected keyword {tok.text!r} at {tok.pos}")
            if self.peek("("):
                raise ParseError(f"calls are not allowed: {tok.text}(...)")
            return Name(tok.text)
        raise ParseError(f"unexpected {tok.text!r} at {tok.pos}")

    def _name(self) -> Name:
        tok = self.take()
        if tok.kind != "name" or tok.text in KEYWORDS:
            raise ParseError("old() takes a variable path")
        return Name(tok.text)


_COMPARE_OPS = frozenset({"==", "!=", "<", "<=", ">", ">="})


def parse(src: str) -> Node:
    if not isinstance(src, str):
        raise ParseError("expression must be a string")
    if len(src) > MAX_LENGTH:
        raise ParseError(f"expression longer than {MAX_LENGTH} characters")
    if not src.strip():
        raise ParseError("empty expression")
    parser = _Parser(_tokenize(src))
    node = parser.expr()
    if parser.peek() is not None:
        raise ParseError(f"unexpected {parser.peek().text!r} at {parser.peek().pos}")
    return node


# --- evaluation -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Env:
    """Where names come from. `now` and `before` look up a variable in the state after and
    before the line ran (raising KeyError if absent); `deref` resolves heap references."""

    now: Callable[[str], Any]
    before: Callable[[str], Any] | None = None
    deref: Callable[[Any], Any] = lambda v: v


def _number(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)


def _check_magnitude(v: Any) -> Any:
    if isinstance(v, float) and not math.isfinite(v):
        raise EvalError("result is not a finite number")
    if _number(v) and abs(v) > MAX_MAGNITUDE:
        raise EvalError("result too large")
    return v


def evaluate(node: Node, env: Env) -> Any:
    return _eval(node, env, old=False)


def _eval(node: Node, env: Env, old: bool) -> Any:
    match node:
        case Lit(value):
            return value
        case Name(name):
            lookup = env.before if old else env.now
            if lookup is None:
                raise EvalError("no 'before' state for old()")
            try:
                return env.deref(lookup(name))
            except KeyError:
                raise EvalError(f"unknown variable {name!r}") from None
        case Old(path):
            return _eval(path, env, old=True)
        case Index(obj, index):
            container, key = _eval(obj, env, old), _eval(index, env, old)
            return env.deref(_index(container, key))
        case Field(obj, name):
            target = _eval(obj, env, old)
            if not isinstance(target, dict) or name not in target:
                raise EvalError(f"value has no field {name!r}")
            return env.deref(target[name])
        case Neg(operand):
            v = _eval(operand, env, old)
            if not _number(v):
                raise EvalError("'-' needs a number")
            return _check_magnitude(-v)
        case BinOp(op, left, right):
            return _arith(op, _eval(left, env, old), _eval(right, env, old))
        case Compare(first, rest):
            left = _eval(first, env, old)
            for op, operand in rest:
                right = _eval(operand, env, old)
                if not _compare(op, left, right):
                    return False
                left = right
            return True
        case BoolOp("and", operands):
            return all(_truth(_eval(o, env, old)) for o in operands)
        case BoolOp("or", operands):
            return any(_truth(_eval(o, env, old)) for o in operands)
        case Not(operand):
            return not _truth(_eval(operand, env, old))
        case Len(operand):
            v = _eval(operand, env, old)
            if not isinstance(v, list | str | dict):
                raise EvalError("len() needs a list, string or map")
            return len(v)
    raise EvalError(f"cannot evaluate {type(node).__name__}")


def _index(container: Any, key: Any) -> Any:
    if isinstance(container, list | str):
        if not isinstance(key, int) or isinstance(key, bool):
            raise EvalError("list index must be an integer")
        if not -len(container) <= key < len(container):
            raise EvalError(f"index {key} out of range")
        return container[key]
    if isinstance(container, dict):
        if key in container:
            return container[key]
        # JSON snapshots store map keys as strings.
        if _number(key) and str(key) in container:
            return container[str(key)]
        raise EvalError(f"key {key!r} not in map")
    raise EvalError("value is not indexable")


def _arith(op: str, a: Any, b: Any) -> Any:
    if not (_number(a) and _number(b)):
        raise EvalError(f"'{op}' needs two numbers")
    if op in ("//", "%") and b == 0:
        raise EvalError("division by zero")
    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "//":
        result = a // b
    else:
        result = a % b
    return _check_magnitude(result)


def _compare(op: str, a: Any, b: Any) -> bool:
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if not ((_number(a) and _number(b)) or (isinstance(a, str) and isinstance(b, str))):
        raise EvalError(f"'{op}' needs two numbers or two strings")
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def _truth(v: Any) -> bool:
    if isinstance(v, bool | int | float | str | list | dict) or v is None:
        return bool(v)
    raise EvalError("value has no truth value")
