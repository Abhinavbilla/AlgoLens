"""The /v1/trace path end to end (jail + driver + tracer), and the traceability check."""

import textwrap

import pytest
from algolens_sandbox.batch import TraceRequest, run_trace
from algolens_sandbox.guard import check_traceable

BUBBLE = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
"""


def tr(source, entry, *args, **kw):
    return run_trace(TraceRequest(source=textwrap.dedent(source), entry=entry,
                                  input={"args": list(args)}, **kw))  # fmt: skip


def test_trace_records_a_real_run_and_matches_the_untraced_result():
    resp = tr(BUBBLE, "bubble_sort", [5, 1, 4, 2, 8])
    assert resp.status == "ok", resp
    assert resp.value == [1, 2, 4, 5, 8]
    frames = resp.trace["frames"]
    assert frames[0]["line"] == 3 and frames[-1]["next"] == "return"
    assert resp.trace["truncated"] is None
    # The swap line only ever runs right after a comparison that chose it.
    for prev, cur in zip(frames, frames[1:], strict=False):
        if cur["line"] == 8:
            assert (prev["line"], prev["next"]) == (7, 8)


def test_trace_is_reproducible():
    a = tr(BUBBLE, "bubble_sort", [3, 1, 2])
    b = tr(BUBBLE, "bubble_sort", [3, 1, 2])
    assert a.trace == b.trace


def test_set_order_in_a_trace_is_reproducible():
    src = "def f():\n    s = {'kiwi', 'fig', 'plum', 'date'}\n    return sorted(s)\n"
    assert tr(src, "f").trace == tr(src, "f").trace


def test_untraced_failure_is_reported_as_such():
    resp = tr("def f(x):\n    return 1 // x\n", "f", 0)
    assert resp.status == "runtime_error"
    assert resp.trace is None


def test_frame_limit_marks_trace_truncated():
    src = "def f(n):\n    t = 0\n    for i in range(n):\n        t += i\n    return t\n"
    resp = tr(src, "f", 10_000, max_frames=100)
    assert resp.status == "ok"
    assert resp.trace["truncated"] == "too_many_frames"
    assert len(resp.trace["frames"]) == 100


def test_trace_too_slow_is_trace_failed_not_a_verdict():
    # Fast untraced, but every recorded frame snapshots a 1,500-item list, so recording
    # 20k frames can't finish in 1 s of CPU. That's "too slow to record", not a failure.
    src = """
    def f(n):
        xs = list(range(1500))
        for i in range(n):
            xs[0] = i
        return xs[0]
    """
    resp = tr(src, "f", 10_000, cpu_ms=1000, max_frames=20_000)
    assert resp.status == "trace_failed", resp
    assert resp.trace is None


def test_rejected_source_never_runs():
    resp = tr("import sys\ndef f():\n    sys.settrace(None)\n    return 1\n", "f")
    assert resp.status == "rejected"
    assert any("sys" in p for p in resp.problems)


# --- traceability check -------------------------------------------------------------------


def test_plain_algorithmic_code_is_traceable():
    src = """
    from collections import deque, defaultdict
    import heapq, math
    from typing import List, Optional
    class ListNode:
        def __init__(self, val=0, next=None):
            self.val = val
            self.next = next
    def solve(grid: List[List[int]]) -> int:
        q = deque([(0, 0)])
        dist = defaultdict(lambda: math.inf)
        h = []
        heapq.heappush(h, (0, 0))
        return len(q) + len(h)
    """
    assert check_traceable(textwrap.dedent(src)) == []


@pytest.mark.parametrize(
    "src",
    [
        "import sys",
        "import os.path",
        "from sys import settrace",
        "from . import x",
        "import inspect",
        "import ctypes",
        "import random",  # answers must not depend on randomness either
        "x = __import__('os')",
        "f = getattr(object, 'x')",
        "setattr(a, 'b', 1)",
        "eval('1')",
        "exec('x=1')",
        "compile('1', 'f', 'eval')",
        "g = globals()",
        "l = locals()",
        "v = vars()",
        "open('/etc/passwd')",
        "breakpoint()",
        "x = (lambda: 0).__code__",
        "x = y.__class__",
        "def f():\n    yield 1\nx = f().gi_frame",
        "x = tb.tb_frame",
        "x = frame.f_back",
        "x = frame.f_locals",
        "x = c.co_consts",
        "x = __builtins__",
        "x = thing.settrace",
        "x = thing._getframe()",
        "x = thing.monitoring",
        "def f(:",
    ],
)
def test_untraceable_code_is_rejected(src):
    assert check_traceable(src) != []


def test_trace_check_judges_many_inputs_in_one_jail():
    from algolens_sandbox.batch import TraceCheckRequest, run_trace_check

    inputs = [{"args": [[3, 1, 2]]}, {"args": [[]]}, {"args": [[5, 4, 3, 2, 1]]}]
    resp = run_trace_check(TraceCheckRequest(source=BUBBLE, entry="bubble_sort", inputs=inputs))
    assert resp.status == "ok", resp
    assert [r.status for r in resp.results] == ["ok", "ok", "ok"]
    assert all(r.frames > 0 for r in resp.results)
    assert resp.results[0].truncated is None


def test_trace_check_reports_failures_per_input():
    from algolens_sandbox.batch import TraceCheckRequest, run_trace_check

    src = "def f(x):\n    return 10 // x\n"
    resp = run_trace_check(TraceCheckRequest(source=src, entry="f",
                                             inputs=[{"args": [2]}, {"args": [0]}]))  # fmt: skip
    assert [r.status for r in resp.results] == ["ok", "runtime_error"]
