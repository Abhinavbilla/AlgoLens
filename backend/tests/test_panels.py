"""The M4 panel kinds, on real recordings from the tracer."""

import pytest

from algolens.animation.builder import AnimationError, build, compile_visual
from tests.test_animation import record


def frames(tmp_path, src, entry, args, panels):
    trace, source = record(tmp_path, src, entry, *args)
    return build(trace, source=source, templates=[], panels=compile_visual({"panels": panels}))[
        "frames"
    ]


def last_panel(fr, i=0):
    return fr[-1]["panels"][i]


def test_stack_and_queue_with_item_text(tmp_path):
    src = """
    from collections import deque
    def f(nums):
        stack = []
        q = deque()
        for i in range(len(nums)):
            stack.append(i)
            q.append(nums[i])
        q.popleft()
        return 0
    """
    fr = frames(tmp_path, src, "f", [[7, 8, 9]], [
        {"kind": "stack", "var": "stack", "item": "nums[item]", "label": "stack (values)"},
        {"kind": "queue", "var": "q"},
    ])  # fmt: skip
    assert last_panel(fr, 0)["items"] == ["7", "8", "9"]  # indices shown as their values
    assert last_panel(fr, 1)["items"] == ["8", "9"]  # front first
    pushed = next(f for f in fr if f["line"] == 6 and f["panels"][0]["items"] == ["7"])
    assert pushed["panels"][0]["changed"] == [0]


def test_linked_list_follows_next_and_shows_pointers(tmp_path):
    src = """
    class ListNode:
        def __init__(self, val, next=None):
            self.val = val
            self.next = next
    def f():
        head = ListNode(1, ListNode(2, ListNode(3)))
        prev = None
        cur = head
        while cur:
            cur.next, prev, cur = prev, cur, cur.next
        return 0
    """
    fr = frames(tmp_path, src, "f", [], [
        {"kind": "linked_list", "var": "prev", "pointers": [{"label": "prev", "at": "prev"},
                                                            {"label": "cur", "at": "cur"}]},
    ])  # fmt: skip
    p = last_panel(fr)
    assert [n["text"] for n in p["nodes"]] == ["3", "2", "1"]
    assert {x["label"]: x["node"] for x in p["pointers"]} == {
        "prev": p["nodes"][0]["id"],
        "cur": None,
    }
    assert p["cycle_to"] is None


def test_linked_list_cycle_is_detected(tmp_path):
    src = """
    class ListNode:
        def __init__(self, val, next=None):
            self.val = val
            self.next = next
    def f():
        a = ListNode(1, ListNode(2))
        a.next.next = a
        return 0
    """
    fr = frames(tmp_path, src, "f", [], [{"kind": "linked_list", "var": "a"}])
    p = last_panel(fr)
    assert [n["text"] for n in p["nodes"]] == ["1", "2"] and p["cycle_to"] == 0


def test_tree_layout_marks_and_pointers(tmp_path):
    src = """
    from collections import deque
    class TreeNode:
        def __init__(self, val, left=None, right=None):
            self.val = val
            self.left = left
            self.right = right
    def f():
        root = TreeNode(2, TreeNode(1), TreeNode(3, None, TreeNode(4)))
        queue = deque([root.left, root.right])
        node = root.right
        return 0
    """
    fr = frames(tmp_path, src, "f", [], [
        {"kind": "tree", "var": "root", "pointers": [{"label": "node", "at": "node"}],
         "marks": [{"label": "in queue", "from": "queue"},
                   {"label": "leaf", "when": "node.left == None and node.right == None"}]},
    ])  # fmt: skip
    p = last_panel(fr)
    by_text = {n["text"]: n for n in p["nodes"]}
    assert [n["text"] for n in sorted(p["nodes"], key=lambda n: n["x"])] == ["1", "2", "3", "4"]
    assert {t: n["y"] for t, n in by_text.items()} == {"1": 1, "2": 0, "3": 1, "4": 2}
    assert by_text["1"]["marks"] == ["in queue", "leaf"]
    assert by_text["3"]["marks"] == ["in queue"]
    assert by_text["4"]["marks"] == ["leaf"]
    assert p["pointers"] == [{"label": "node", "node": by_text["3"]["id"]}]
    assert {(e["from"], e["to"]) for e in p["edges"]} == {
        (by_text["2"]["id"], by_text["1"]["id"]), (by_text["2"]["id"], by_text["3"]["id"]),
        (by_text["3"]["id"], by_text["4"]["id"])}  # fmt: skip


def test_graph_marks_labels_and_fixed_layout(tmp_path):
    src = """
    def f(n, edges):
        dist = [-1] * n
        dist[0] = 0
        heap = [(4, 2), (1, 1)]
        u = 0
        return 0
    """
    panel = {"kind": "graph", "nodes": "n", "edges": "edges", "node_label": "dist[node]",
             "pointers": [{"label": "u", "at": "u"}],
             "marks": [{"label": "in heap", "from": "heap", "item": "item[1]"},
                       {"label": "reached", "when": "dist[node] != -1"}]}  # fmt: skip
    fr = frames(tmp_path, src, "f", [3, [[0, 1, 5], [1, 2, 7]]], [panel])
    p = last_panel(fr)
    assert [n["label"] for n in p["nodes"]] == ["0", "-1", "-1"]
    assert [n["marks"] for n in p["nodes"]] == [["reached"], ["in heap"], ["in heap"]]
    assert p["edges"] == [{"u": 0, "v": 1, "w": "5"}, {"u": 1, "v": 2, "w": "7"}]
    assert p["pointers"] == [{"label": "u", "node": 0}]
    positions = {(n["x"], n["y"]) for f in fr for n in f["panels"][0].get("nodes", [])}
    assert len(positions) == 3  # the same three positions in every frame


def test_grid_text_marks_pointer_and_headers(tmp_path):
    src = """
    from collections import deque
    def f(grid, word):
        dist = [[-1] * len(grid[0]) for _ in grid]
        dist[0][0] = 0
        queue = deque([(0, 1)])
        r, c = 0, 0
        return 0
    """
    panel = {"kind": "grid", "var": "dist", "text": "dist[row][col]", "hide_when": "dist[row][col] == -1",
             "marks": [{"label": "wall", "when": "grid[row][col] == '#'"},
                       {"label": "queued", "from": "queue"}],
             "pointers": [{"label": "here", "row": "r", "col": "c"}],
             "col_header": {"text": "word", "offset": 1}}  # fmt: skip
    fr = frames(tmp_path, src, "f", [[[".", ".", "#"]], "ab"], [panel])
    p = last_panel(fr)
    assert [c["text"] for c in p["rows"][0]] == ["0", "", ""]
    assert [c["marks"] for c in p["rows"][0]] == [[], ["queued"], ["wall"]]
    assert p["pointers"] == [{"label": "here", "row": 0, "col": 0}]
    assert p["col_header"] == ["", "a", "b"]
    changed = next(f for f in fr if f["line"] == 4)["panels"][0]["rows"][0][0]
    assert changed["changed"] is True


@pytest.mark.parametrize(
    "panel",
    [
        {"kind": "chart", "var": "x"},
        {"kind": "tree", "var": "root.left"},
        {"kind": "tree", "var": "root", "pointers": [{"label": "p", "at": "a.b"}]},
        {"kind": "graph", "nodes": "n"},
        {"kind": "grid", "var": "len(g)"},
        {"kind": "stack", "var": "s", "item": "__import__('os')"},
        {"kind": "vars", "vars": ["ok", "not ok"]},
    ],
)
def test_bad_visual_specs_are_rejected(panel):
    with pytest.raises(AnimationError):
        compile_visual({"panels": [panel]})
