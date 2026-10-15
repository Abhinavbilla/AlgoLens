"""The solve pipeline end to end with scripted AI replies and the real sandbox (plan §6)."""

import os
import threading
from collections import deque

import pytest

from algolens.ai.budget import Budget
from algolens.ai.client import AIClient
from algolens.pipeline import prompts
from algolens.pipeline.solve import solve
from algolens.sandbox.client import SandboxClient

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")
pytestmark = pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")

STATEMENT = (
    "Given an integer array nums, find the subarray with the largest sum, and return its sum.\n"
    "Example: nums = [-2,1,-3,4,-1,2,1,-5,4] -> 6"
)

SPEC = {
    "in_scope": True,
    "title": "Maximum Subarray",
    "function_name": "max_sub_array",
    "params": [
        {
            "name": "nums",
            "type": {
                "kind": "array",
                "of": {"kind": "int", "min": -10000, "max": 10000},
                "len": {"min": 1, "max": 100000},
            },
        }
    ],
    "constraints": [],
    "output": "the largest subarray sum",
    "comparator": {"kind": "exact"},
    "examples": [
        {"args": [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], "expected": 6},
        {"args": [[1]], "expected": 1},
    ],
    "patterns": ["dp"],
}

BRUTE_PY = """
def max_sub_array(nums):
    best = nums[0]
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            best = max(best, total)
    return best
"""

BRUTE_CPP = """
#include <algolens.h>
#include <algorithm>
long long max_sub_array(const std::vector<long long>& nums) {
    long long best = nums[0];
    for (size_t i = 0; i < nums.size(); ++i) {
        long long total = 0;
        for (size_t j = i; j < nums.size(); ++j) { total += nums[j]; best = std::max(best, total); }
    }
    return best;
}
int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    algolens::emit(algolens::Json(max_sub_array(nums)).dump());
}
"""

BRUTE_B_PY = """
def max_sub_array(nums):
    return max(sum(nums[i:j]) for i in range(len(nums)) for j in range(i + 1, len(nums) + 1))
"""


def kadane(best_init: str = "nums[0]", cpp_plus: str = "") -> dict:
    py = f"""
def max_sub_array(nums):
    best = {best_init}
    current = 0
    for x in nums:
        current = max(x, current + x)
        best = max(best, current)
    return best
"""
    cpp = f"""
#include <algolens.h>
#include <algorithm>
long long max_sub_array(const std::vector<long long>& nums) {{
    long long best = {best_init}, current = 0;
    for (long long x : nums) {{ current = std::max(x, current + x); best = std::max(best, current); }}
    return best{cpp_plus};
}}
int main() {{
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    algolens::emit(algolens::Json(max_sub_array(nums)).dump());
}}
"""
    return {"name": "Kadane", "key_idea": "Extend or restart the running sum.", "time": "O(n)",
            "space": "O(1)", "python_code": py, "cpp_code": cpp}  # fmt: skip


BRUTE = {"name": "Brute force", "key_idea": "Try every subarray.", "time": "O(n^2)",
         "space": "O(1)", "python_code": BRUTE_PY, "cpp_code": BRUTE_CPP}  # fmt: skip


class Script:
    """Scripted replies per role, in order; the last reply repeats once the queue runs dry."""

    def __init__(self, **replies):
        self.queues = {
            role: deque(r if isinstance(r, list) else [r]) for role, r in replies.items()
        }
        self.calls: list[str] = []
        self.prompts: dict[str, list[str]] = {}
        self.lock = threading.Lock()

    def __call__(self, role: str, system: str, prompt: str) -> dict:
        with self.lock:
            self.calls.append(role)
            self.prompts.setdefault(role, []).append(prompt)
            q = self.queues[role]
            return q.popleft() if len(q) > 1 else q[0]


def run(script: Script, limit: int = 200_000, max_repairs: int = 2):
    roles = {r: "fake:test" for r in ("parse", "brute_a", "brute_b", "approaches", "checker",
                                       "repair", "narration", "explain")}  # fmt: skip
    progress: list[tuple] = []
    result = solve(STATEMENT, AIClient(roles, fake=script), SandboxClient(SOCKET), Budget(limit),
                   progress=lambda *a: progress.append(a), max_repairs=max_repairs)  # fmt: skip
    return result, progress


def thinking(intuition: str, ds: dict | None = None) -> dict:
    return {
        "intuition": intuition,
        "bottleneck": "It repeats work.",
        "data_structure": ds,
        "steps": ["Look at each value.", "Keep the best sum."],
        "complexity_reasoning": "One loop.",
    }


EXPLANATION = {
    "understanding": {"restated": "Find the biggest total of consecutive values.",
                      "inputs_outputs": "A list of integers in, one integer out.",
                      "observations": ["A run can start anywhere."], "edge_cases": ["All negative."]},
    "approaches": [thinking("Try every start and end."), thinking("Extend or restart the run.")],
    "pattern": "Kadane's algorithm",
    "takeaway": "Keep the best run ending here.",
}  # fmt: skip


def happy(**overrides) -> Script:
    replies = {
        "parse": SPEC,
        "brute_a": BRUTE,
        "brute_b": {"restatement": "max sum of a contiguous run", "python_code": BRUTE_B_PY},
        "approaches": {"approaches": [kadane()]},
        "repair": kadane(),
        "explain": EXPLANATION,
    }
    replies.update(overrides)
    return Script(**replies)


def test_kadane_is_verified_with_the_brute_force():
    result, progress = run(happy())
    assert result.status == "done", result.reason
    brute, fast = result.approaches
    assert brute.is_brute and brute.status == "verified", brute.reason
    assert fast.status == "verified", fast.reason
    assert fast.tests_passed == 300 and fast.examples_checked == 2 and fast.repairs == 0
    stages = {p[0] for p in progress}
    assert {"reading the problem", "writing solutions", "checking Kadane"} <= stages
    assert any(p[1] == p[2] == 302 for p in progress)  # per-test progress was reported
    assert result.tokens["used"] > 0


def test_brute_b_never_sees_the_parsed_spec():
    script = happy()
    run(script)
    prompt = script.prompts["brute_b"][0]
    assert STATEMENT in prompt and '"params"' not in prompt and "Parsed description" not in prompt


def test_wrong_approach_is_repaired():
    result, _ = run(happy(approaches={"approaches": [kadane(best_init="0")]}))
    fast = result.approaches[1]
    assert fast.status == "verified" and fast.repairs == 1, fast.reason


def test_repair_that_never_converges_stays_unverified_with_the_failing_input():
    buggy = kadane(best_init="0")
    result, _ = run(happy(approaches={"approaches": [buggy]}, repair=buggy))
    fast = result.approaches[1]
    assert fast.status == "unverified" and fast.repairs == 2
    assert fast.reason.startswith("Wrong on input") and fast.failing_case["expected"] < 0
    assert result.approaches[0].status == "verified"


def test_brute_forces_that_disagree_leave_everything_unverified():
    # Allows the empty subarray: right on the examples, wrong when every number is negative.
    lenient = "def max_sub_array(nums):\n    return max([0] + [sum(nums[i:j]) for i in range(len(nums)) for j in range(i + 1, len(nums) + 1)])\n"
    result, _ = run(happy(brute_b={"restatement": "", "python_code": lenient}))
    assert all(a.status == "unverified" for a in result.approaches)
    assert "disagree" in result.approaches[0].reason
    assert result.approaches[0].failing_case["second"] == 0


def test_brute_force_that_fails_an_example_is_regenerated_once():
    wrong = {**BRUTE, "python_code": "def max_sub_array(nums):\n    return sum(nums)\n"}
    script = happy(brute_a=[wrong, BRUTE])
    result, _ = run(script)
    assert result.approaches[0].status == "verified" and result.approaches[0].repairs == 1
    assert "got this worked example wrong" in script.prompts["brute_a"][1]
    assert result.approaches[1].status == "verified"


def test_brute_force_wrong_twice_means_nothing_is_verified():
    wrong = {**BRUTE, "python_code": "def max_sub_array(nums):\n    return sum(nums)\n"}
    result, _ = run(happy(brute_a=wrong))
    assert all(a.status == "unverified" for a in result.approaches)
    assert "worked example wrong" in result.approaches[1].reason


def test_out_of_scope_statement_is_rejected():
    result, _ = run(
        Script(parse={"in_scope": False, "rejection_reason": "This is a geometry proof."})
    )
    assert result.status == "rejected" and result.reason == "This is a geometry proof."


def test_examples_that_break_the_schema_are_reparsed_then_rejected():
    bad = {**SPEC, "examples": [{"args": [[]], "expected": 0}]}  # empty, but len min is 1
    script = Script(parse=bad)
    result, _ = run(script)
    assert result.status == "rejected" and "worked example 1" in result.reason
    assert script.calls.count("parse") == 2
    assert "Your previous answer had this problem" in script.prompts["parse"][1]


def test_budget_runs_out_after_reading_the_problem():
    # Room for the parse call's worst case, but not for the larger solution-writing calls.
    parse_reserve = (len(prompts.PARSE_SYSTEM) + len(prompts.parse_prompt(STATEMENT))) // 3 + 8000
    script = happy()
    result, _ = run(script, limit=parse_reserve + 200)
    assert result.status == "failed" and "budget" in result.reason
    assert result.approaches == [] and "approaches" not in script.calls


def test_budget_too_small_to_read_the_problem():
    result, _ = run(happy(), limit=5000)
    assert result.status == "failed" and "reading the problem" in result.reason


def test_cpp_that_disagrees_with_python_is_not_verified():
    off = kadane(cpp_plus=" + 1")
    result, _ = run(happy(approaches={"approaches": [off]}, repair=off), max_repairs=1)
    fast = result.approaches[1]
    assert fast.status == "unverified" and "C++ version disagrees" in fast.reason


def test_permissive_checker_is_rejected():
    spec = {**SPEC, "comparator": {"kind": "checker"}}
    lax = {"python_code": "def check(nums, output):\n    return True\n"}
    result, _ = run(happy(parse=spec, checker=lax))
    assert all(a.status == "unverified" for a in result.approaches)
    assert "too lenient" in result.approaches[0].reason


def test_strict_checker_lets_approaches_verify():
    spec = {**SPEC, "comparator": {"kind": "checker"}}
    strict = {"python_code": BRUTE_PY.replace("max_sub_array(nums)", "_best(nums)")
              + "\ndef check(nums, output):\n    return output == _best(nums)\n"}  # fmt: skip
    result, _ = run(happy(parse=spec, checker=strict))
    assert [a.status for a in result.approaches] == ["verified", "verified"], result.failures


def test_the_thought_process_follows_the_verified_approaches():
    script = happy()
    result, progress = run(script)
    e = result.explanation
    assert e["pattern"] == "Kadane's algorithm"
    assert [a["name"] for a in e["approaches"]] == ["Brute force", "Kadane"]
    assert [a["is_brute"] for a in e["approaches"]] == [True, False]
    assert e["approaches"][1]["time"] == "O(n)"
    prompt = script.prompts["explain"][0]
    assert "Approach 1: Brute force" in prompt and "Approach 2: Kadane" in prompt
    assert "writing the explanation" in {p[0] for p in progress}


def test_a_mismatched_explanation_is_left_out():
    one = {**EXPLANATION, "approaches": EXPLANATION["approaches"][:1]}
    result, _ = run(happy(explain=one))
    assert result.explanation is None
    assert any("explanation unavailable" in f for f in result.failures)
    assert [a.status for a in result.approaches] == ["verified", "verified"]  # results still stand


def test_unverified_approaches_are_not_explained():
    buggy = kadane(best_init="0")
    script = happy(approaches={"approaches": [buggy]}, repair=buggy,
                   explain={**EXPLANATION, "approaches": EXPLANATION["approaches"][:1]})  # fmt: skip
    result, _ = run(script)
    assert [a["name"] for a in result.explanation["approaches"]] == ["Brute force"]
    assert "Approach 2" not in script.prompts["explain"][0]
