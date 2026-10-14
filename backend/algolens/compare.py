"""The compare view: how each verified approach's work grows with input size (plan §7.6).

Each approach runs once per size on the same generated input, counting executed lines of the
solution with sys.monitoring in the sandbox (the same count the animation's step counter
uses). An approach is dropped at the sizes it can't finish within the time limit, and the
chart says so.
"""

import threading
from collections import OrderedDict

from algolens.pipeline.service import input_rules
from algolens.pipeline.visualize import sandbox_extras
from algolens.sandbox.client import SandboxClient
from algolens.schema.generate import GenerationError, Profile
from algolens.schema.service import generate_tests
from algolens.verification.runner import run_tests

SIZES = (10, 30, 100, 300, 1000, 3000)
LIMITS = {"cpu_ms": 4000, "wall_ms": 8000, "mem_mb": 512}
SEED = 7


def input_size(args: list) -> int:
    """The size of an input: its largest top-level collection (list or string length; for a
    grid, its rows; for a tree, its level-order length), or the largest integer argument
    when there's no collection."""
    sizes = [len(a) for a in args if isinstance(a, list | str)]
    if sizes:
        return max(sizes)
    ints = [a for a in args if isinstance(a, int) and not isinstance(a, bool)]
    return max(ints) if ints else 0


def scaling_inputs(spec: dict, sandbox: SandboxClient) -> list[tuple[int, list]]:
    """One input per distinct size; sizes the schema can't reach collapse into one."""
    rules = input_rules(spec)
    out: dict[int, list] = {}
    for size in SIZES:
        try:
            args = generate_tests(rules, 1, SEED + size, sandbox, profile=Profile(size=size))[0]
        except GenerationError:
            continue
        n = input_size(args)
        if n not in out:
            out[n] = args
    return sorted(out.items())


def compare(spec: dict, approaches: list[dict], sandbox: SandboxClient) -> dict:
    """approaches: [{"id", "name", "python_code"}] (verified ones)."""
    inputs = scaling_inputs(spec, sandbox)
    tests = [{"id": f"n{n}", "input": {"args": args}, "count": True} for n, args in inputs]
    extras = sandbox_extras(spec)
    series = []
    for a in approaches:
        results = run_tests(sandbox, "python", a["python_code"], spec["function_name"], tests,
                            extras, per_test=LIMITS)  # fmt: skip
        points = []
        for (n, _), r in zip(inputs, results, strict=True):
            if r["outcome"] == "ok" and r.get("ops") is not None:
                points.append({"n": n, "ops": r["ops"], "status": "ok"})
            else:
                status = "too slow" if r["outcome"] in ("timeout", "not_run") else r["outcome"]
                points.append({"n": n, "ops": None, "status": status})
        series.append({"id": a["id"], "name": a["name"], "points": points})
    return {"sizes": [n for n, _ in inputs], "series": series,
            "limits": {"cpu_ms": LIMITS["cpu_ms"]}}  # fmt: skip


_cache: OrderedDict[str, dict] = OrderedDict()
_lock = threading.Lock()


def cached_compare(key: str, spec: dict, approaches: list[dict]) -> dict:
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    client = SandboxClient()
    try:
        result = compare(spec, approaches, client)
    finally:
        client.close()
    with _lock:
        _cache[key] = result
        while len(_cache) > 64:
            _cache.popitem(last=False)
    return result
