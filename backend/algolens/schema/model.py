"""Input schema language (plan §5): describes a problem's parameters so that we, not the AI,
generate random tests and check edited inputs.

A schema is JSON:

    {"params": [{"name": "nums", "type": {...}}, ...],
     "constraints": [{"check": "k <= len(nums)", "message": "k can't exceed the length of nums"}]}

Types ("kind"), with their options:
    int        min, max                         (defaults ±10^9)
    float      min, max
    bool
    string     len {min,max}, chars, valid_parentheses
               chars: lowercase | uppercase | letters | digits | alnum | binary | parens |
                      any other string = the exact allowed characters
    array      of <type>, len {min,max}, sorted ("asc"/"desc"/true), distinct, permutation
               permutation: {"start": 0 or 1} -> values are start .. start+len-1, shuffled
    matrix     of <type>, rows {min,max}, cols {min,max}           (rectangular list of lists)
    grid       chars (e.g. "01" or ".#"), rows, cols   (list of lists of 1-character strings)
    linked_list of <type>, len                                      (given as a list)
    binary_tree of <type>, nodes {min,max}, bst                     (level order, null for gaps)
    edges      nodes (count; usually the name of an earlier int param), count {min,max},
               directed, weighted, weight {min,max}, connected, dag, tree, self_loops, duplicates
    ops        ops [{"name": ..., "args": [<type>, ...]}], len     (list of [name, *args])
               shaped like a class-style design problem (constructor + method calls) so those
               can reuse it later; nothing class-specific is built yet.

Any bound may be an integer or an expression over *earlier* parameters, in the narration
expression language (e.g. "len(nums)", "n - 1"). `constraints` are boolean expressions over
all parameters. Rules this language can't express go in an optional validator (see
algolens/schema/service.py), which runs in the sandbox.
"""

from dataclasses import dataclass, field
from typing import Any

from algolens.narration import expr
from algolens.narration.expr import ExprError, Node

DEFAULT_INT = 10**9
MAX_LEN = 10**6
CHARSETS = {
    "lowercase": "abcdefghijklmnopqrstuvwxyz",
    "uppercase": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "letters": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "digits": "0123456789",
    "alnum": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "binary": "01",
    "parens": "()",
}


class SchemaError(ValueError):
    """The schema itself is malformed (a bug in the schema, not in an input)."""


Bound = int | Node


@dataclass(frozen=True)
class Range:
    min: Bound
    max: Bound
    source: tuple[Any, Any] = (None, None)


@dataclass(frozen=True)
class IntT:
    min: Bound = -DEFAULT_INT
    max: Bound = DEFAULT_INT


@dataclass(frozen=True)
class FloatT:
    min: Bound = -DEFAULT_INT
    max: Bound = DEFAULT_INT


@dataclass(frozen=True)
class BoolT:
    pass


@dataclass(frozen=True)
class StringT:
    len: Range
    chars: str
    chars_name: str
    valid_parentheses: bool = False


@dataclass(frozen=True)
class ArrayT:
    of: "TypeSpec"
    len: Range
    sorted: str | None = None  # "asc" | "desc"
    distinct: bool = False
    permutation_start: int | None = None


@dataclass(frozen=True)
class MatrixT:
    of: "TypeSpec"
    rows: Range
    cols: Range


@dataclass(frozen=True)
class GridT:
    chars: str
    rows: Range
    cols: Range


@dataclass(frozen=True)
class LinkedListT:
    of: "TypeSpec"
    len: Range


@dataclass(frozen=True)
class TreeT:
    of: "TypeSpec"
    nodes: Range
    bst: bool = False


@dataclass(frozen=True)
class EdgesT:
    nodes: Bound
    count: Range
    directed: bool = False
    weighted: bool = False
    weight: IntT = field(default_factory=lambda: IntT(1, 100))
    connected: bool = False
    dag: bool = False
    tree: bool = False
    self_loops: bool = False
    duplicates: bool = False


@dataclass(frozen=True)
class OpSpec:
    name: str
    args: tuple["TypeSpec", ...]


@dataclass(frozen=True)
class OpsT:
    ops: tuple[OpSpec, ...]
    len: Range


TypeSpec = (
    IntT | FloatT | BoolT | StringT | ArrayT | MatrixT | GridT | LinkedListT | TreeT | EdgesT | OpsT
)


@dataclass(frozen=True)
class Param:
    name: str
    type: TypeSpec


@dataclass(frozen=True)
class Constraint:
    check: Node
    source: str
    message: str


@dataclass(frozen=True)
class Schema:
    params: tuple[Param, ...]
    constraints: tuple[Constraint, ...]

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.params]


# --- compiling ---------------------------------------------------------------------------------


def compile_schema(raw: dict) -> Schema:
    if not isinstance(raw, dict) or not isinstance(raw.get("params"), list) or not raw["params"]:
        raise SchemaError("schema needs a non-empty `params` list")
    params, seen = [], []
    for i, p in enumerate(raw["params"]):
        name = p.get("name") if isinstance(p, dict) else None
        if not isinstance(name, str) or not name.isidentifier() or name.startswith("_"):
            raise SchemaError(f"param {i}: invalid name {name!r}")
        if name in seen:
            raise SchemaError(f"param {name!r} is defined twice")
        params.append(Param(name, _type(p.get("type"), f"param {name!r}", seen)))
        seen.append(name)
    constraints = []
    for i, c in enumerate(raw.get("constraints", [])):
        source = c.get("check") if isinstance(c, dict) else c
        try:
            node = expr.parse(source)
        except ExprError as exc:
            raise SchemaError(f"constraint {i}: {exc}") from exc
        _check_names(node, seen, f"constraint {i}")
        message = c.get("message") if isinstance(c, dict) else None
        constraints.append(Constraint(node, source, message or f"must satisfy {source}"))
    return Schema(tuple(params), tuple(constraints))


def _type(raw: Any, where: str, earlier: list[str]) -> TypeSpec:
    if not isinstance(raw, dict) or "kind" not in raw:
        raise SchemaError(f"{where}: type needs a `kind`")
    kind = raw["kind"]
    b = lambda key, default: _bound(raw.get(key, default), f"{where}.{key}", earlier)  # noqa: E731
    r = lambda key, lo, hi: _range(raw.get(key, {}), f"{where}.{key}", earlier, lo, hi)  # noqa: E731
    of = lambda: _type(raw.get("of"), f"{where}.of", earlier)  # noqa: E731
    flag = lambda key: _flag(raw, key, where)  # noqa: E731
    match kind:
        case "int":
            return IntT(b("min", -DEFAULT_INT), b("max", DEFAULT_INT))
        case "float":
            return FloatT(b("min", -DEFAULT_INT), b("max", DEFAULT_INT))
        case "bool":
            return BoolT()
        case "string":
            name = raw.get("chars", "lowercase")
            if not isinstance(name, str) or not name:
                raise SchemaError(f"{where}.chars must be a non-empty string")
            chars = CHARSETS.get(name, name)
            parens = flag("valid_parentheses")
            if parens and set(chars) - set("()"):
                raise SchemaError(f'{where}: valid_parentheses needs chars "parens"')
            return StringT(r("len", 0, 20), "".join(dict.fromkeys(chars)), name, parens)
        case "array":
            srt = raw.get("sorted")
            srt = "asc" if srt is True else (None if srt in (None, False) else srt)
            if srt not in (None, "asc", "desc"):
                raise SchemaError(f'{where}.sorted must be "asc", "desc" or true')
            perm = raw.get("permutation")
            start = None
            if perm:
                start = perm.get("start", 0) if isinstance(perm, dict) else 0
                if start not in (0, 1):
                    raise SchemaError(f"{where}.permutation.start must be 0 or 1")
            item = of()
            if start is not None and not isinstance(item, IntT):
                raise SchemaError(f"{where}: a permutation must be of ints")
            if (srt or flag("distinct")) and not isinstance(item, IntT | FloatT | StringT | BoolT):
                raise SchemaError(f"{where}: sorted/distinct need scalar items")
            return ArrayT(item, r("len", 0, 20), srt, flag("distinct"), start)
        case "matrix":
            return MatrixT(of(), r("rows", 1, 5), r("cols", 1, 5))
        case "grid":
            chars = raw.get("chars", "01")
            if not isinstance(chars, str) or not chars:
                raise SchemaError(f"{where}.chars must be a non-empty string")
            return GridT("".join(dict.fromkeys(chars)), r("rows", 1, 5), r("cols", 1, 5))
        case "linked_list":
            return LinkedListT(of(), r("len", 0, 20))
        case "binary_tree":
            item = of()
            if flag("bst") and not isinstance(item, IntT):
                raise SchemaError(f"{where}: a bst must hold ints")
            return TreeT(item, r("nodes", 0, 15), flag("bst"))
        case "edges":
            if "nodes" not in raw:
                raise SchemaError(f"{where}: edges need `nodes` (a count or an earlier param)")
            w = raw.get("weight", {"min": 1, "max": 100})
            weight = IntT(_bound(w.get("min", 1), f"{where}.weight.min", earlier),
                          _bound(w.get("max", 100), f"{where}.weight.max", earlier))  # fmt: skip
            spec = EdgesT(
                nodes=b("nodes", None), count=r("count", 0, 20), directed=flag("directed"),
                weighted=flag("weighted"), weight=weight, connected=flag("connected"),
                dag=flag("dag"), tree=flag("tree"), self_loops=flag("self_loops"),
                duplicates=flag("duplicates"),
            )  # fmt: skip
            if spec.dag and not spec.directed:
                raise SchemaError(f"{where}: dag needs directed")
            if spec.tree and spec.directed:
                raise SchemaError(f"{where}: tree is for undirected edges")
            return spec
        case "ops":
            specs = raw.get("ops")
            if not isinstance(specs, list) or not specs:
                raise SchemaError(f"{where}: ops needs a non-empty `ops` list")
            ops = []
            for j, o in enumerate(specs):
                name = o.get("name") if isinstance(o, dict) else None
                if not isinstance(name, str) or not name.isidentifier():
                    raise SchemaError(f"{where}.ops[{j}]: invalid name")
                ops.append(OpSpec(name, tuple(_type(a, f"{where}.ops[{j}]", earlier)
                                              for a in o.get("args", []))))  # fmt: skip
            return OpsT(tuple(ops), r("len", 1, 20))
    raise SchemaError(f"{where}: unknown kind {kind!r}")


def _flag(raw: dict, key: str, where: str) -> bool:
    v = raw.get(key, False)
    if not isinstance(v, bool):
        raise SchemaError(f"{where}.{key} must be true or false")
    return v


def _bound(v: Any, where: str, earlier: list[str]) -> Bound:
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        try:
            node = expr.parse(v)
        except ExprError as exc:
            raise SchemaError(f"{where}: {exc}") from exc
        _check_names(node, earlier, where)
        return node
    raise SchemaError(f"{where}: expected an integer or an expression, got {v!r}")


def _range(v: Any, where: str, earlier: list[str], lo: int, hi: int) -> Range:
    if isinstance(v, int) and not isinstance(v, bool):
        return Range(v, v, (v, v))
    if not isinstance(v, dict):
        raise SchemaError(f'{where}: expected {{"min": .., "max": ..}}')
    mn, mx = v.get("min", lo), v.get("max", hi)
    rng = Range(_bound(mn, f"{where}.min", earlier), _bound(mx, f"{where}.max", earlier), (mn, mx))
    fixed = isinstance(rng.min, int) and isinstance(rng.max, int)
    if fixed and (rng.min < 0 or rng.min > rng.max or rng.max > MAX_LEN):
        raise SchemaError(f"{where}: need 0 <= min <= max <= {MAX_LEN}")
    return rng


def _check_names(node: Node, allowed: list[str], where: str) -> None:
    for name in _names(node):
        if name not in allowed:
            raise SchemaError(f"{where}: {name!r} isn't an earlier parameter")


def _names(node: Node) -> set[str]:
    match node:
        case expr.Name(name):
            return {name}
        case expr.Lit():
            return set()
        case expr.Index(obj, index):
            return _names(obj) | _names(index)
        case expr.Field(obj, _) | expr.Neg(obj) | expr.Not(obj) | expr.Len(obj):
            return _names(obj)
        case expr.Old(path):
            return _names(path)
        case expr.BinOp(_, left, right):
            return _names(left) | _names(right)
        case expr.Compare(first, rest):
            return _names(first).union(*(_names(n) for _, n in rest))
        case expr.BoolOp(_, operands):
            return set().union(*(_names(n) for n in operands))
    return set()


def resolve(bound: Bound, values: dict[str, Any]) -> int:
    """An integer bound, evaluating expressions over the parameters generated so far."""
    if isinstance(bound, int):
        return bound
    try:
        v = expr.evaluate(bound, expr.Env(now=values.__getitem__))
    except ExprError as exc:
        raise ValueError(str(exc)) from exc
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if not isinstance(v, int) or isinstance(v, bool):
        raise ValueError(f"bound evaluated to {v!r}, not an integer")
    return v
