"""Compare view (M7): sys.monitoring counts, scaling runs."""

import os

import pytest

from algolens.compare import compare, input_size
from algolens.config import get_settings
from algolens.library.loader import load_all
from algolens.sandbox.client import SandboxClient
from algolens.verification.runner import run_tests
from tests.test_solve import BRUTE_PY, SPEC, kadane

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")
needs_sandbox = pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")


def test_input_size():
    assert input_size([[1, 2, 3], 7]) == 3
    assert input_size(["abcd"]) == 4
    assert input_size([[[1, 2], [3, 4], [5, 6]]]) == 3
    assert input_size([5, [[0, 1]]]) == 1  # a collection wins over a plain integer
    assert input_size([12]) == 12
    assert input_size([True]) == 0


@needs_sandbox
def test_monitoring_count_equals_the_animation_step_count_on_every_library_input():
    """Plan §7.6: the compare chart's count and the player's step count must agree."""
    client = SandboxClient(SOCKET)
    checked = 0
    for entry in load_all(get_settings().library_dir):
        inputs = [entry.default_input] + entry.tests
        tests = [{"id": f"t{i}", "input": inp, "count": True} for i, inp in enumerate(inputs)]
        counted = run_tests(client, "python", entry.python_code, entry.entry, tests,
                            entry.sandbox_extras())  # fmt: skip
        for inp, c in zip(inputs, counted, strict=True):
            resp = client.trace({"source": entry.python_code, "entry": entry.entry,
                                 "input": inp, **entry.sandbox_extras()})  # fmt: skip
            if resp["status"] != "ok" or resp["trace"].get("truncated"):
                continue
            assert c["outcome"] == "ok", (entry.slug, inp, c)
            assert c["ops"] == len(resp["trace"]["frames"]), (entry.slug, inp)
            checked += 1
    assert checked >= 60


@needs_sandbox
def test_scaling_runs_cover_two_orders_of_magnitude():
    approaches = [
        {"id": "b", "name": "Brute force", "python_code": BRUTE_PY},
        {"id": "k", "name": "Kadane", "python_code": kadane()["python_code"]},
    ]
    result = compare(SPEC, approaches, SandboxClient(SOCKET))
    sizes = result["sizes"]
    assert len(sizes) >= 4 and sizes[-1] / sizes[0] >= 100
    brute, fast = result["series"]
    fast_ops = {p["n"]: p["ops"] for p in fast["points"]}
    assert all(p["status"] == "ok" for p in fast["points"])
    # Kadane is linear: 3 lines per element plus a constant.
    assert fast_ops[sizes[-1]] == 3 * sizes[-1] + 4
    finished = [p for p in brute["points"] if p["status"] == "ok"]
    assert len(finished) >= 3
    big = finished[-1]
    assert big["ops"] > 10 * fast_ops[big["n"]]  # quadratic pulls away
    assert all(p["status"] in ("ok", "too slow") for p in brute["points"])
