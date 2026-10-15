"""Animation builder and narration engine, on real recordings from the tracer module.

The tracer's own semantics are pinned by sandbox/tests/test_tracer.py on Python 3.12.
"""

import importlib.util
import json
import os
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

from algolens.animation.builder import (
    AnimationError,
    before_view,
    build,
    compile_visual,
    nearest_cpp_line,
)
from algolens.animation.values import FrameView
from algolens.config import get_settings
from algolens.library.loader import LibraryError, load_all, load_entry
from algolens.narration.engine import compile_templates, lint

REPO = Path(__file__).resolve().parents[2]
LIBRARY = get_settings().library_dir
TRACER_DIR = Path(os.environ.get("ALGOLENS_TRACER_DIR", REPO / "sandbox" / "driver"))
sys.path.insert(0, str(TRACER_DIR))
from tracer import Recorder  # noqa: E402

# The sandbox driver defines these for solutions and builds them from JSON (driver.py);
# the same here so library entries with tree / linked-list inputs record the same way.
PRELUDE = """
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
"""


def _to_nodes(module, kind, value):
    if kind == "linked_list":
        head = None
        for v in reversed(value):
            head = module.ListNode(v, head)
        return head
    if kind == "binary_tree":
        if not value:
            return None
        root = module.TreeNode(value[0])
        queue, i = [root], 1
        while queue and i < len(value):
            node = queue.pop(0)
            for side in ("left", "right"):
                if i < len(value) and value[i] is not None:
                    setattr(node, side, module.TreeNode(value[i]))
                    queue.append(getattr(node, side))
                i += 1
        return root
    return value


def record(tmp_path, src, entry, *args, convert=()):
    path = tmp_path / "solution.py"
    path.write_text(textwrap.dedent(src).lstrip("\n"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(PRELUDE, "<prelude>", "exec"), module.__dict__)
    spec.loader.exec_module(module)
    args = [_to_nodes(module, convert[i] if i < len(convert) else None, a)
            for i, a in enumerate(args)]  # fmt: skip
    rec = Recorder(str(path))
    rec.start()
    try:
        getattr(module, entry)(*args)
    finally:
        rec.stop()
    return rec.result(), path.read_text(encoding="utf-8")


def animate_library(tmp_path, slug, args=None):
    entry = load_entry(LIBRARY / slug)
    args = args if args is not None else entry.default_input["args"]
    trace, source = record(tmp_path, entry.python_code, entry.entry, *json.loads(json.dumps(args)))
    return build(trace, source=source, templates=compile_templates(entry.narration),
                 panels=compile_visual(entry.visual), cpp_lines=entry.cpp_line_map())  # fmt: skip


def texts(animation):
    return [f["narration"]["text"] for f in animation["frames"]]


# --- library entries ----------------------------------------------------------------------


def test_all_library_entries_load():
    entries = load_all(LIBRARY)
    assert [e.slug for e in entries] == [
        "bubble-sort", "insertion-sort", "merge-sort", "quick-sort", "binary-search",
        "two-pointers", "sliding-window", "prefix-sums", "hash-map-counting", "monotonic-stack",
        "valid-anagram", "count-bits", "heap-operations", "grid-bfs", "graph-dfs", "dijkstra",
        "topological-sort", "union-find", "reverse-linked-list", "fast-slow-pointers",
        "level-order", "preorder-traversal", "inorder-traversal", "postorder-traversal",
        "bst-insert-search", "house-robber", "lcs", "coin-change", "knapsack", "merge-intervals",
        "subsets", "permutations", "segment-tree",
    ]  # fmt: skip


def test_two_pointers_animation(tmp_path):
    anim = animate_library(tmp_path, "two-pointers")
    frames = anim["frames"]
    assert len(frames) <= 300
    assert frames[0]["narration"]["text"] == "Put l at the first position and r at the last one, 5."
    # Computed values always show their operands.
    assert "Add the two ends: 1 + 11 = 12." in texts(anim)
    # old() reads the value from before the line ran.
    assert "l moves from 0 to 1." in texts(anim)
    assert frames[-1]["next"] == "return" and frames[-1]["ret"] == "[2, 4]"
    array = frames[0]["panels"][0]
    assert array["items"] == ["1", "3", "4", "6", "9", "11"]
    assert {p["label"]: p["index"] for p in array["pointers"]} == {"l": 0, "r": 5}


def test_bubble_sort_narration_follows_the_branch_taken(tmp_path):
    anim = animate_library(tmp_path, "bubble-sort", [[2, 1, 3]])
    for f in anim["frames"]:
        if f["line"] == 6:
            text = f["narration"]["text"]
            if f["next"] == 7:
                assert "swap them" in text
            else:
                assert "already in order" in text
    swap = next(f for f in anim["frames"] if f["line"] == 7)
    assert swap["panels"][0]["changed"] == [0, 1]  # the two swapped cells, nothing else
    assert swap["narration"]["text"] == "Swapped: 1 now comes before 2."


def test_binary_search_range_and_pointers(tmp_path):
    anim = animate_library(tmp_path, "binary-search")
    first = anim["frames"][0]["panels"][0]
    assert first["range"] == {"label": "still searching", "from": 0, "to": 7}
    assert anim["frames"][-1]["ret"] == "3"


def test_every_frame_maps_to_exactly_one_recorded_frame(tmp_path):
    entry = load_entry(LIBRARY / "bubble-sort")
    trace, source = record(tmp_path, entry.python_code, entry.entry, [3, 1, 2])
    anim = build(trace, source=source, templates=compile_templates(entry.narration),
                 panels=compile_visual(entry.visual), cpp_lines=entry.cpp_line_map())  # fmt: skip
    assert [(f["line"], f["next"]) for f in anim["frames"]] == [
        (f["line"], f["next"]) for f in trace["frames"]
    ]
    for built, raw in zip(anim["frames"], trace["frames"], strict=True):
        arr = FrameView(raw, trace["heap"]).plain(raw["stack"][0]["locals"]["arr"])
        assert built["panels"][0]["items"] == [str(x) for x in arr]


def test_library_narration_lints_clean(tmp_path):
    for entry in load_all(LIBRARY):
        args = json.loads(json.dumps(entry.default_input["args"]))
        convert = entry.sandbox_extras().get("convert", [])
        trace, _ = record(tmp_path, entry.python_code, entry.entry, *args, convert=convert)
        views = [FrameView(f, trace["heap"]) for f in trace["frames"]]
        befores = [before_view(views[i - 1] if i else None, v) for i, v in enumerate(views)]
        report = lint(compile_templates(entry.narration), views, befores)
        assert report["errors"] == [], (entry.slug, report)
        assert report["coverage"] >= 0.8, (entry.slug, report)


# --- narration rules ----------------------------------------------------------------------

SRC = """
def f(a):
    x = 1
    x = x + a
    return x
"""


def test_template_with_a_number_not_from_the_state_falls_back_to_neutral(tmp_path):
    trace, source = record(tmp_path, SRC, "f", 5)
    templates = compile_templates([{"line": 3, "text": "Step 2: x is now {x}."}])
    anim = build(trace, source=source, templates=templates, panels=[])
    frame = anim["frames"][1]
    assert frame["narration"] == {"source": "neutral", "text": "X changed from 1 to 6"}


def test_neutral_sentence_describes_only_recorded_changes(tmp_path):
    trace, source = record(tmp_path, SRC, "f", 5)
    anim = build(trace, source=source, templates=[], panels=[])
    assert texts(anim) == ["Nothing changed", "X changed from 1 to 6", "Returned 6"]


def test_when_condition_must_be_true_on_the_frame(tmp_path):
    trace, source = record(tmp_path, SRC, "f", 5)
    templates = compile_templates([
        {"line": 3, "when": "x > 100", "text": "x is huge: {x}"},
        {"line": 3, "when": "x <= 100", "text": "x is {x}"},
    ])  # fmt: skip
    anim = build(trace, source=source, templates=templates, panels=[])
    assert anim["frames"][1]["narration"]["text"] == "x is 6"


def test_lint_flags_overlapping_templates_that_disagree(tmp_path):
    trace, _ = record(tmp_path, SRC, "f", 5)
    views = [FrameView(f, trace["heap"]) for f in trace["frames"]]
    befores = [before_view(views[i - 1] if i else None, v) for i, v in enumerate(views)]
    templates = compile_templates([
        {"line": 3, "text": "x grows to {x}"},
        {"line": 3, "text": "x becomes {x}"},
    ])  # fmt: skip
    report = lint(templates, views, befores)
    assert any("all apply but differ" in e for e in report["errors"])


def test_lint_flags_ungrounded_numbers(tmp_path):
    trace, _ = record(tmp_path, SRC, "f", 5)
    views = [FrameView(f, trace["heap"]) for f in trace["frames"]]
    befores = [before_view(views[i - 1] if i else None, v) for i, v in enumerate(views)]
    report = lint(compile_templates([{"line": 3, "text": "x is 42"}]), views, befores)
    assert any("not from the state" in e for e in report["errors"])


# --- limits and helpers -------------------------------------------------------------------


def test_more_than_300_frames_is_too_long(tmp_path):
    src = "def f(n):\n    t = 0\n    for i in range(n):\n        t += i\n    return t\n"
    trace, source = record(tmp_path, src, "f", 200)
    with pytest.raises(AnimationError) as exc:
        build(trace, source=source, templates=[], panels=[])
    assert exc.value.code == "too_long"


def test_truncated_recording_is_never_animated(tmp_path):
    trace, source = record(tmp_path, SRC, "f", 5)
    trace["truncated"] = "too_many_frames"
    with pytest.raises(AnimationError):
        build(trace, source=source, templates=[], panels=[])


def test_nearest_cpp_line():
    mapping = {2: 7, 5: 10}
    assert nearest_cpp_line(mapping, 2) == 7
    assert nearest_cpp_line(mapping, 4) == 7
    assert nearest_cpp_line(mapping, 9) == 10
    assert nearest_cpp_line(mapping, 1) is None


def test_broken_library_entry_is_rejected(tmp_path):
    folder = tmp_path / "broken"
    shutil.copytree(LIBRARY / "two-pointers", folder)
    meta = json.loads((folder / "entry.json").read_text(encoding="utf-8"))
    meta["narration"].append({"line": 99, "text": "nowhere"})
    (folder / "entry.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(LibraryError, match="line 99"):
        load_entry(folder)


def test_visual_spec_can_only_name_paths():
    with pytest.raises(AnimationError):
        compile_visual({"panels": [{"kind": "array", "var": "len(nums) + 1"}]})
    with pytest.raises(AnimationError):
        compile_visual({"panels": [{"kind": "chart", "var": "x"}]})


def test_small_constants_show_the_working_and_sentence_numbers_stay_rejected(tmp_path):
    trace, source = record(tmp_path, SRC, "f", 5)
    ok = compile_templates([{"line": 3, "text": "position {x + 1} comes next"}])
    anim = build(trace, source=source, templates=ok, panels=[])
    assert anim["frames"][1]["narration"]["text"] == "position 6 + 1 = 7 comes next"
    # The same number typed into the sentence is still rejected (neutral fallback).
    bad = compile_templates([{"line": 3, "text": "position {x} + 1 comes next"}])
    anim = build(trace, source=source, templates=bad, panels=[])
    assert anim["frames"][1]["narration"]["source"] == "neutral"


def test_nested_lists_in_narration_are_fully_decoded(tmp_path):
    src = "def f():\n    dp = [[0, 1], [2, 3]]\n    return 0\n"
    trace, source = record(tmp_path, src, "f")
    templates = compile_templates([{"line": 2, "text": "dp is {dp} and row {dp[1]}"}])
    anim = build(trace, source=source, templates=templates, panels=[])
    assert anim["frames"][0]["narration"]["text"] == "dp is [[0, 1], [2, 3]] and row [2, 3]"


def test_a_map_with_a_key_called_ref_is_not_mistaken_for_a_reference(tmp_path):
    src = "def f():\n    m = {'ref': 5, 'tuple': 6}\n    return 0\n"
    trace, source = record(tmp_path, src, "f")
    templates = compile_templates([{"line": 2, "text": "m is {m}"}])
    anim = build(trace, source=source, templates=templates, panels=[])
    assert anim["frames"][0]["narration"]["text"] == "m is {'ref': 5, 'tuple': 6}"
