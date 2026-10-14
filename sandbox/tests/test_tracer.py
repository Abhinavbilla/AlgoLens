"""Golden tests pinning what a frame shows (plan §7.2). Changing the frame definition must
change these on purpose.

A frame is the line that just finished in some activation, the values after it ran, and the
line that activation runs next ("return" when it returns).
"""

import importlib.util
import sys
import textwrap

import pytest

sys.path.insert(0, "/opt/algolens/driver")
from tracer import Recorder  # noqa: E402

RETURN = "return"


def trace(tmp_path, src, entry, *args, max_frames=5000):
    path = tmp_path / "solution.py"
    path.write_text(textwrap.dedent(src).lstrip("\n"))
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rec = Recorder(str(path), max_frames=max_frames)
    rec.start()
    try:
        value = getattr(module, entry)(*args)
    finally:
        rec.stop()
    return value, rec


def resolve(v, frame, heap):
    """Decode an encoded value as it was at `frame`."""
    if isinstance(v, dict):
        if "ref" in v:
            content = heap[f"{v['ref']}.{frame['objects'][str(v['ref'])]}"]
            if content["type"] == "dict":
                return {resolve(k, frame, heap): resolve(x, frame, heap)
                        for k, x in content["items"]}  # fmt: skip
            if content["type"] == "object":
                return {k: resolve(x, frame, heap) for k, x in content["fields"].items()}
            return [resolve(x, frame, heap) for x in content["items"]]
        if "tuple" in v:
            return tuple(resolve(x, frame, heap) for x in v["tuple"])
        return v
    return v


def steps(rec, with_values=True):
    """(function, line, next, locals of the activation that ran the line) per frame."""
    out = []
    for f in rec.frames:
        act = next(a for a in f["stack"] if a["aid"] == f["aid"])
        row = (act["fn"], f["line"], f["next"])
        if with_values:
            row += ({k: resolve(v, f, rec.heap) for k, v in act["locals"].items()},)
        out.append(row)
    return out


# --- §7.2 golden cases -------------------------------------------------------------------


def test_straight_line_shows_values_after_each_line(tmp_path):
    src = """
    def f(a):
        x = 1
        x = x + a
        return x
    """
    value, rec = trace(tmp_path, src, "f", 5)
    assert value == 6
    assert steps(rec) == [
        ("f", 2, 3, {"a": 5, "x": 1}),
        ("f", 3, 4, {"a": 5, "x": 6}),  # x is already 6: values are *after* line 3 ran
        ("f", 4, RETURN, {"a": 5, "x": 6}),
    ]
    assert rec.frames[-1]["ret"] == 6


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        (-1, [("sign", 2, 3), ("sign", 3, 6), ("sign", 6, RETURN)]),
        (1, [("sign", 2, 5), ("sign", 5, 6), ("sign", 6, RETURN)]),
    ],
    ids=["if-branch", "else-branch"],
)
def test_if_else_next_line_identifies_the_branch(tmp_path, arg, expected):
    src = """
    def sign(x):
        if x < 0:
            s = "neg"
        else:
            s = "pos"
        return s
    """
    _, rec = trace(tmp_path, src, "sign", arg)
    assert steps(rec, with_values=False) == expected


def test_for_loop_including_final_failed_check(tmp_path):
    src = """
    def total(n):
        t = 0
        for i in range(n):
            t += i
        return t
    """
    _, rec = trace(tmp_path, src, "total", 2)
    assert steps(rec) == [
        ("total", 2, 3, {"n": 2, "t": 0}),
        ("total", 3, 4, {"n": 2, "t": 0, "i": 0}),
        ("total", 4, 3, {"n": 2, "t": 0, "i": 0}),
        ("total", 3, 4, {"n": 2, "t": 0, "i": 1}),
        ("total", 4, 3, {"n": 2, "t": 1, "i": 1}),
        ("total", 3, 5, {"n": 2, "t": 1, "i": 1}),  # loop exhausted: next is the return
        ("total", 5, RETURN, {"n": 2, "t": 1, "i": 1}),
    ]


def test_while_loop_including_final_failed_check(tmp_path):
    src = """
    def countdown(n):
        while n > 0:
            n -= 1
        return n
    """
    _, rec = trace(tmp_path, src, "countdown", 2)
    assert steps(rec) == [
        ("countdown", 2, 3, {"n": 2}),
        ("countdown", 3, 2, {"n": 1}),
        ("countdown", 2, 3, {"n": 1}),
        ("countdown", 3, 2, {"n": 0}),
        ("countdown", 2, 4, {"n": 0}),  # condition false: next is the return
        ("countdown", 4, RETURN, {"n": 0}),
    ]


def test_line_that_calls_a_helper_finishes_after_the_helper(tmp_path):
    src = """
    def double(x):
        y = x * 2
        return y
    def f(a):
        b = double(a)
        return b + 1
    """
    value, rec = trace(tmp_path, src, "f", 3)
    assert value == 7
    assert steps(rec) == [
        ("double", 2, 3, {"x": 3, "y": 6}),
        ("double", 3, RETURN, {"x": 3, "y": 6}),
        ("f", 5, 6, {"a": 3, "b": 6}),  # f's line 5 finishes only once double returned
        ("f", 6, RETURN, {"a": 3, "b": 6}),
    ]
    # While double runs, the call stack shows f still sitting on line 5.
    for frame in rec.frames[:2]:
        assert [(a["fn"], a["line"]) for a in frame["stack"]] == [
            ("f", 5),
            ("double", frame["line"]),
        ]
    assert [len(f["stack"]) for f in rec.frames] == [2, 2, 1, 1]


def test_recursion_three_levels_deep(tmp_path):
    src = """
    def fact(n):
        if n <= 1:
            return 1
        return n * fact(n - 1)
    """
    value, rec = trace(tmp_path, src, "fact", 3)
    assert value == 6
    assert [(f["aid"], f["line"], f["next"]) for f in rec.frames] == [
        (0, 2, 4),
        (1, 2, 4),
        (2, 2, 3),
        (2, 3, RETURN),
        (1, 4, RETURN),
        (0, 4, RETURN),
    ]
    assert [f.get("ret") for f in rec.frames] == [None, None, None, 1, 2, 6]
    deepest = rec.frames[2]["stack"]
    assert [(a["fn"], a["line"], a["locals"]["n"]) for a in deepest] == [
        ("fact", 4, 3),
        ("fact", 4, 2),
        ("fact", 2, 1),
    ]


def test_return_inside_a_loop(tmp_path):
    src = """
    def first_even(xs):
        for x in xs:
            if x % 2 == 0:
                return x
        return None
    """
    value, rec = trace(tmp_path, src, "first_even", [1, 4, 5])
    assert value == 4
    assert steps(rec, with_values=False) == [
        ("first_even", 2, 3),
        ("first_even", 3, 2),  # 1 is odd: back to the loop
        ("first_even", 2, 3),
        ("first_even", 3, 4),  # 4 is even
        ("first_even", 4, RETURN),
    ]


def test_caught_exception(tmp_path):
    src = """
    def safe_div(a, b):
        try:
            q = a // b
        except ZeroDivisionError:
            q = None
        return q
    """
    value, rec = trace(tmp_path, src, "safe_div", 1, 0)
    assert value is None
    assert steps(rec, with_values=False) == [
        ("safe_div", 2, 3),
        ("safe_div", 3, None),  # didn't finish normally...
        ("safe_div", 4, 5),
        ("safe_div", 5, 6),
        ("safe_div", 6, RETURN),
    ]
    assert rec.frames[1]["raised"] == "ZeroDivisionError"


# --- values and objects ------------------------------------------------------------------


def test_list_mutation_is_versioned_and_earlier_frames_are_unchanged(tmp_path):
    src = """
    def swap_first(arr):
        arr[0], arr[1] = arr[1], arr[0]
        arr.append(9)
        return arr
    """
    _, rec = trace(tmp_path, src, "swap_first", [1, 2])
    arr = [resolve(f["stack"][0]["locals"]["arr"], f, rec.heap) for f in rec.frames]
    assert arr == [[2, 1], [2, 1, 9], [2, 1, 9]]


def test_aliases_share_one_object(tmp_path):
    src = """
    def alias(a):
        b = a
        b.append(1)
        return len(a)
    """
    _, rec = trace(tmp_path, src, "alias", [])
    last = rec.frames[-1]["stack"][0]["locals"]
    assert last["a"] == last["b"] == {"ref": 0}


def test_cyclic_linked_list_resolves_to_the_frame_state(tmp_path):
    src = """
    class ListNode:
        def __init__(self, val):
            self.val = val
            self.next = None
    def make_cycle():
        a = ListNode(1)
        b = ListNode(2)
        a.next = b
        b.next = a
        a.val = 10
        return a.val
    """
    _, rec = trace(tmp_path, src, "make_cycle")
    frames = [f for f in rec.frames if f["stack"][-1]["fn"] == "make_cycle"]
    last = frames[-1]
    a = last["stack"][-1]["locals"]["a"]
    a_content = rec.heap[f"{a['ref']}.{last['objects'][str(a['ref'])]}"]
    b_ref = a_content["fields"]["next"]["ref"]
    b_content = rec.heap[f"{b_ref}.{last['objects'][str(b_ref)]}"]
    assert a_content["fields"]["val"] == 10
    assert b_content["fields"]["next"] == {"ref": a["ref"]}  # cycle back to a, by number


def test_recording_never_calls_solution_dunder_methods(tmp_path):
    src = """
    calls = []
    class Evil:
        def __init__(self):
            self.v = 1
        def __repr__(self):
            calls.append("repr"); raise RuntimeError
        def __eq__(self, other):
            calls.append("eq"); raise RuntimeError
        def __hash__(self):
            calls.append("hash"); raise RuntimeError
        def __getattribute__(self, name):
            if name != "v" and not name.startswith("__"):
                calls.append("getattribute:" + name)
            return object.__getattribute__(self, name)
    class EvilList(list):
        def __iter__(self):
            calls.append("iter"); raise RuntimeError
    def run():
        e = Evil()
        lst = EvilList([1, 2])
        d = {1: e}
        return len(calls)
    """
    value, rec = trace(tmp_path, src, "run")
    assert value == 0  # no dunder or iteration hook of the solution was ever called
    # Evil.__init__ is solution code too, so it is traced like everything else.
    assert [f["stack"][-1]["fn"] for f in rec.frames] == ["__init__"] + ["run"] * 4


def test_traced_and_untraced_results_match(tmp_path):
    src = """
    def work(n):
        seen = {}
        out = []
        for i in range(n):
            seen[i % 3] = seen.get(i % 3, 0) + i
            out.append(sorted(seen.items()))
        return out
    """
    traced, _ = trace(tmp_path, src, "work", 10)
    path = tmp_path / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert traced == module.work(10)


def test_too_many_frames_stops_recording_but_not_the_code(tmp_path):
    src = """
    def busy(n):
        t = 0
        for i in range(n):
            t += i
        return t
    """
    value, rec = trace(tmp_path, src, "busy", 1000, max_frames=50)
    assert value == sum(range(1000))
    assert rec.truncated == "too_many_frames"
    assert len(rec.frames) == 50


def test_huge_snapshot_stops_recording(tmp_path):
    src = """
    def big():
        xs = list(range(5000))
        return len(xs)
    """
    value, rec = trace(tmp_path, src, "big")
    assert value == 5000
    assert rec.truncated == "snapshot_too_large"


def test_non_json_values_are_encoded_safely(tmp_path):
    src = """
    from collections import deque
    def mixed():
        big = 2 ** 70
        inf = float("inf")
        t = (1, [2])
        q = deque([3])
        s = {4}
        f = len
        return 0
    """
    _, rec = trace(tmp_path, src, "mixed")
    loc = rec.frames[-1]["stack"][0]["locals"]
    assert loc["big"] == {"int": str(2**70)}
    assert loc["inf"] == {"float": "inf"}
    assert loc["t"]["tuple"][0] == 1 and "ref" in loc["t"]["tuple"][1]
    assert loc["f"] == {"opaque": "builtin_function_or_method"}
    frame = rec.frames[-1]
    assert resolve(loc["q"], frame, rec.heap) == [3]
    assert resolve(loc["s"], frame, rec.heap) == [4]
