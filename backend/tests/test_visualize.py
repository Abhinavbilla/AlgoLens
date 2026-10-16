"""Animations for generated approaches: AI plans are checked like library entries (M6)."""

import pytest

from algolens.pipeline.visualize import culprits
from tests.test_solve import SOCKET, happy, kadane, run

VISUAL = {
    "panels": [
        {"kind": "array", "var": "nums", "pointers": []},
        {"kind": "vars", "vars": ["x", "current", "best"]},
    ]
}
# kadane() source lines: 2 def, 3 best = ..., 4 current = 0, 5 for, 6 current = ..., 7 best = ..., 8 return
GOOD = [
    {"line": 6, "text": "Extend the run or restart at {x}: current is {current}."},
    {"line": 7, "text": "The best sum so far is {best}."},
]
PLAN = {"visual": VISUAL, "narration": GOOD, "cpp_lines": {"6": 6, "7": 6, "99": 1}}

needs_sandbox = pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")


def _fast(result):
    return result.approaches[1]


@needs_sandbox
def test_good_plan_is_used_as_written():
    result, progress = run(happy(narration=PLAN))
    anim = _fast(result).animation
    assert anim["source"] == "ai" and anim["narration"] == GOOD and anim["visual"] == VISUAL
    # The out-of-range AI pair is dropped; the computed alignment covers every code line.
    assert "99" not in anim["cpp_lines"] and anim["cpp_lines"]["6"] == 6
    assert {"2", "3", "4", "5", "6", "7", "8"} <= set(anim["cpp_lines"])
    assert anim["default_input"] == {"args": [[1]]}  # the shortest worked example
    assert "preparing animations" in {p[0] for p in progress}
    assert result.approaches[0].animation["source"] == "ai"  # the brute force too


@needs_sandbox
def test_broken_visual_falls_back_to_a_generic_one():
    bad = {**PLAN, "visual": {"panels": [{"kind": "hologram", "var": "nums"}]}}
    script = happy(narration=bad)
    result, _ = run(script)
    anim = _fast(result).animation
    assert script.calls.count("narration") == 4  # two tries per verified approach
    assert "visual: panel 0: unknown kind" in script.prompts["narration"][1]
    assert anim["source"] == "ai+generic visual" and anim["narration"] == GOOD
    kinds = [p["kind"] for p in anim["visual"]["panels"]]
    assert kinds[0] == "array" and kinds[-1] == "vars"


@needs_sandbox
def test_ungrounded_narration_is_dropped_not_shown():
    lying = {**PLAN, "narration": [*GOOD, {"line": 3, "text": "Start with 42."}]}
    result, _ = run(happy(narration=lying))
    anim = _fast(result).animation
    assert anim["narration"] == GOOD and anim["lint"]["dropped"] == [2]
    assert "some narration dropped" in anim["source"]


@needs_sandbox
def test_unusable_reply_gets_a_generic_animation():
    result, _ = run(happy(narration={"nonsense": True}))
    anim = _fast(result).animation
    assert anim["source"] == "generic" and anim["narration"] == []
    assert anim["visual"]["panels"]


@needs_sandbox
def test_unverified_approaches_are_not_animated():
    buggy = kadane(best_init="0")
    result, _ = run(happy(approaches={"approaches": [buggy]}, repair=buggy, narration=PLAN))
    assert _fast(result).status == "unverified" and _fast(result).animation is None
    assert result.approaches[0].animation is not None


def test_culprits_for_lint_errors():
    errors = [
        "template 3 at line 7: number(s) ['42'] not from the state in 'x'",
        "line 5: templates [1, 4, 2] all apply but differ: ['a', 'b']",
    ]
    assert culprits(errors) == {3, 2, 4}


def test_braced_panel_expressions_are_unwrapped():
    from algolens.pipeline.visualize import unwrap_braces

    raw = {"panels": [{"kind": "array", "var": "{nums}", "pointers": [{"label": "i", "at": "{i + 1}"}]},
                      {"kind": "vars", "vars": ["x"]}]}  # fmt: skip
    out = unwrap_braces(raw)
    assert out["panels"][0]["var"] == "nums" and out["panels"][0]["pointers"][0]["at"] == "i + 1"
    assert unwrap_braces("{a} and {b}") == "{a} and {b}"  # only one enclosing pair is removed
