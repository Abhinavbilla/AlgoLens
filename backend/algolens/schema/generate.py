"""Random inputs from a schema (plan §5).

Two profiles:
- small (default): sizes kept small enough for a brute force to run, values mostly from a
  small window, biased toward the cases that break code: minimum sizes, duplicates,
  all-equal values and range extremes. Always within the declared constraints.
- size=n: collections get exactly n elements (clamped to the declared range), for the
  operation-count chart in M7.

Generation is deterministic for a given seed. Every generated input is checked with
validate() before it's returned, so a generator bug can't produce an invalid test.
"""

import random
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
from algolens.schema.validate import validate

SMALL_LEN = 8
SMALL_GRID = 4
SMALL_NODES = 8
SMALL_EDGES = 12
SMALL_WINDOW = 20  # values mostly within ±20 of zero (or of the range's edge)
ATTEMPTS = 200


class GenerationError(ValueError):
    """Couldn't produce inputs that satisfy the schema (it may be contradictory)."""


@dataclass(frozen=True)
class Profile:
    size: int | None = None  # None = small profile

    @property
    def small(self) -> bool:
        return self.size is None


SMALL = Profile()


def generate(schema: Schema, rng: random.Random, profile: Profile = SMALL) -> list[Any]:
    """One input, as the argument list in parameter order."""
    last_error = "no attempt made"
    for _ in range(ATTEMPTS):
        try:
            args = _attempt(schema, rng, profile)
        except _Retry as exc:
            last_error = str(exc)
            continue
        issues = validate(schema, args)
        if not issues:
            return args
        last_error = str(issues[0])
    raise GenerationError(f"couldn't generate a valid input in {ATTEMPTS} tries: {last_error}")


def generate_many(schema: Schema, n: int, seed: int, profile: Profile = SMALL) -> list[list[Any]]:
    rng = random.Random(seed)
    return [generate(schema, rng, profile) for _ in range(n)]


class _Retry(Exception):
    pass


def _attempt(schema: Schema, rng: random.Random, profile: Profile) -> list[Any]:
    values: dict[str, Any] = {}
    for p in schema.params:
        values[p.name] = _gen(p.type, rng, profile, values)
    for c in schema.constraints:
        try:
            if evaluate(c.check, Env(now=values.__getitem__)) is not True:
                raise _Retry(c.message)
        except ExprError as exc:
            raise _Retry(str(exc)) from exc
    return [values[p.name] for p in schema.params]


def _bounds(r: Range, env: dict, small_cap: int, profile: Profile) -> tuple[int, int]:
    try:
        lo, hi = resolve(r.min, env), resolve(r.max, env)
    except ValueError as exc:
        raise _Retry(str(exc)) from exc
    lo = max(lo, 0)
    if hi < lo:
        raise _Retry(f"empty size range {lo}..{hi}")
    if profile.small:
        hi = min(hi, max(lo, small_cap))
    return lo, hi


def _size(r: Range, env: dict, rng: random.Random, profile: Profile, small_cap: int) -> int:
    lo, hi = _bounds(r, env, small_cap, profile)
    if not profile.small:
        return max(lo, min(hi, profile.size))
    roll = rng.random()
    if roll < 0.12:
        return lo  # smallest allowed: empty arrays, single nodes...
    if roll < 0.20:
        return hi
    return rng.randint(lo, hi)


def _int_range(t: IntT | FloatT, env: dict) -> tuple[int, int]:
    try:
        lo, hi = resolve(t.min, env), resolve(t.max, env)
    except ValueError as exc:
        raise _Retry(str(exc)) from exc
    if lo > hi:
        raise _Retry(f"empty value range {lo}..{hi}")
    return lo, hi


def _small_window(lo: int, hi: int) -> tuple[int, int]:
    """Where small-profile values mostly come from: around 0 if the range includes it,
    otherwise next to the range's nearest edge."""
    centre = 0 if lo <= 0 <= hi else (lo if lo > 0 else hi)
    return max(lo, centre - SMALL_WINDOW), min(hi, centre + SMALL_WINDOW)


def _gen_int(
    t: IntT, rng: random.Random, profile: Profile, env: dict, pool: list | None = None
) -> int:
    lo, hi = _int_range(t, env)
    if pool:
        return rng.choice(pool)
    if profile.small:
        roll = rng.random()
        if roll < 0.06:
            return lo
        if roll < 0.12:
            return hi
        wlo, whi = _small_window(lo, hi)
        return rng.randint(wlo, whi)
    return rng.randint(lo, hi)


def _gen(t: TypeSpec, rng: random.Random, profile: Profile, env: dict) -> Any:
    match t:
        case IntT():
            return _gen_int(t, rng, profile, env)
        case FloatT():
            lo, hi = _int_range(t, env)
            if profile.small:
                lo, hi = _small_window(lo, hi)
            return round(rng.uniform(lo, hi), 3)
        case BoolT():
            return rng.random() < 0.5
        case StringT():
            n = _size(t.len, env, rng, profile, SMALL_LEN)
            if t.valid_parentheses:
                return _parens(n, rng)
            alphabet = t.chars
            if profile.small and len(alphabet) > 3 and rng.random() < 0.5:
                alphabet = "".join(rng.sample(alphabet, 3))  # few distinct letters: repeats
            return "".join(rng.choice(alphabet) for _ in range(n))
        case ArrayT():
            return _array(t, rng, profile, env)
        case MatrixT():
            rows = _size(t.rows, env, rng, profile, SMALL_GRID)
            cols = _size(t.cols, env, rng, profile, SMALL_GRID)
            return [[_gen(t.of, rng, profile, env) for _ in range(cols)] for _ in range(rows)]
        case GridT():
            rows = _size(t.rows, env, rng, profile, SMALL_GRID)
            cols = _size(t.cols, env, rng, profile, SMALL_GRID)
            return [[rng.choice(t.chars) for _ in range(cols)] for _ in range(rows)]
        case LinkedListT():
            n = _size(t.len, env, rng, profile, SMALL_LEN)
            return [_gen(t.of, rng, profile, env) for _ in range(n)]
        case TreeT():
            return _tree(t, rng, profile, env)
        case EdgesT():
            return _edges(t, rng, profile, env)
        case OpsT():
            n = _size(t.len, env, rng, profile, SMALL_LEN)
            out = []
            for _ in range(n):
                spec = rng.choice(t.ops)
                out.append([spec.name, *(_gen(a, rng, profile, env) for a in spec.args)])
            return out
    raise _Retry(f"can't generate {type(t).__name__}")


def _array(t: ArrayT, rng: random.Random, profile: Profile, env: dict) -> list:
    n = _size(t.len, env, rng, profile, SMALL_LEN)
    if t.permutation_start is not None:
        values = list(range(t.permutation_start, t.permutation_start + n))
        rng.shuffle(values)
        return values
    if t.distinct:
        if isinstance(t.of, IntT):
            lo, hi = _int_range(t.of, env)
            if profile.small:
                wlo, whi = _small_window(lo, hi)
                if whi - wlo + 1 >= n:
                    lo, hi = wlo, whi
            if hi - lo + 1 < n:
                raise _Retry(f"only {hi - lo + 1} distinct values fit, need {n}")
            values = rng.sample(range(lo, hi + 1), n)
        else:
            seen, values = set(), []
            for _ in range(n * 50):
                if len(values) == n:
                    break
                x = _gen(t.of, rng, profile, env)
                if x not in seen:
                    seen.add(x)
                    values.append(x)
            if len(values) < n:
                raise _Retry("couldn't find enough distinct values")
    else:
        pool = None
        if profile.small and isinstance(t.of, IntT) and n > 1:
            roll = rng.random()
            if roll < 0.08:
                pool = [_gen_int(t.of, rng, profile, env)]  # all equal
            elif roll < 0.35:
                pool = [
                    _gen_int(t.of, rng, profile, env) for _ in range(max(2, n // 3))
                ]  # duplicates
        values = [_gen_int(t.of, rng, profile, env, pool) if isinstance(t.of, IntT)
                  else _gen(t.of, rng, profile, env) for _ in range(n)]  # fmt: skip
    if t.sorted:
        values.sort(reverse=t.sorted == "desc")
    return values


def _parens(n: int, rng: random.Random) -> str:
    n -= n % 2
    out, open_, closed = [], 0, 0
    while len(out) < n:
        can_open = open_ < n // 2
        if can_open and (open_ == closed or rng.random() < 0.5):
            out.append("(")
            open_ += 1
        else:
            out.append(")")
            closed += 1
    return "".join(out)


def _tree(t: TreeT, rng: random.Random, profile: Profile, env: dict) -> list:
    n = _size(t.nodes, env, rng, profile, SMALL_NODES)
    if n == 0:
        return []
    # Random shape: each new node hangs off a random free child slot.
    left: dict[int, int] = {}
    right: dict[int, int] = {}
    free = [(0, "L"), (0, "R")]
    for node in range(1, n):
        parent, side = free.pop(rng.randrange(len(free)))
        (left if side == "L" else right)[parent] = node
        free += [(node, "L"), (node, "R")]
    if t.bst:
        lo, hi = _int_range(t.of, env)
        if profile.small:
            wlo, whi = _small_window(lo, hi)
            if whi - wlo + 1 >= n:
                lo, hi = wlo, whi
        if hi - lo + 1 < n:
            raise _Retry("not enough distinct values for a BST")
        ordered = sorted(rng.sample(range(lo, hi + 1), n))
        value: dict[int, Any] = {}
        it = iter(ordered)

        def assign(x: int | None) -> None:
            if x is None:
                return
            assign(left.get(x))
            value[x] = next(it)
            assign(right.get(x))

        assign(0)
    else:
        value = {x: _gen(t.of, rng, profile, env) for x in range(n)}
    # Level order with nulls for missing children, trailing nulls dropped.
    out, queue = [], [0]
    while queue:
        x = queue.pop(0)
        if x is None:
            out.append(None)
            continue
        out.append(value[x])
        queue += [left.get(x), right.get(x)]
    while out and out[-1] is None:
        out.pop()
    return out


def _edges(t: EdgesT, rng: random.Random, profile: Profile, env: dict) -> list:
    try:
        n = resolve(t.nodes, env)
    except ValueError as exc:
        raise _Retry(str(exc)) from exc
    lo, hi = _bounds(t.count, env, SMALL_EDGES, profile)
    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    def key(u: int, v: int) -> tuple[int, int]:
        return (u, v) if t.directed else (min(u, v), max(u, v))

    def add(u: int, v: int) -> bool:
        if u == v and not t.self_loops:
            return False
        k = key(u, v)
        if k in seen and not t.duplicates:
            return False
        if t.dag and order[u] >= order[v]:
            return False
        seen.add(k)
        pairs.append((u, v))
        return True

    order = list(range(n))
    rng.shuffle(order)
    order = {node: i for i, node in enumerate(order)}  # a hidden topological order for dags
    if (t.connected or t.tree) and n > 1:
        nodes = list(range(n))
        rng.shuffle(nodes)
        for i in range(1, n):  # random spanning tree first
            u, v = nodes[i], nodes[rng.randrange(i)]
            if t.dag and order[u] > order[v]:
                u, v = v, u
            add(u, v)
    if t.tree:
        target = len(pairs)  # exactly the spanning tree
    elif profile.small:
        target = rng.randint(max(lo, len(pairs)), max(hi, len(pairs)))
    else:
        target = max(len(pairs), lo, min(hi, profile.size or 0))
    tries = 0
    while len(pairs) < target and n > 0 and tries < 50 * (target + 1):
        tries += 1
        add(rng.randrange(n), rng.randrange(n))
    edges = []
    for u, v in pairs:
        if not t.directed and rng.random() < 0.5:
            u, v = v, u  # undirected edges come either way round
        edges.append([u, v, _gen_int(t.weight, rng, profile, env)] if t.weighted else [u, v])
    rng.shuffle(edges)
    return edges
