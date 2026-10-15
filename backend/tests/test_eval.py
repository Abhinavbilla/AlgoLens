"""`algolens eval` with scripted AI replies: the report's numbers come from real runs."""

import json

import pytest

from algolens.ai.client import AIClient
from algolens.evaluation import run_eval, summarize
from algolens.sandbox.client import SandboxClient
from tests.test_solve import SOCKET, STATEMENT, happy

ROLES = ("parse", "brute_a", "brute_b", "approaches", "checker", "repair", "narration", "explain")
REFERENCE = """
def reference(nums):
    best, cur = nums[0], 0
    for x in nums:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
"""
# Accepts the empty subarray: wrong when every number is negative.
WRONG_REFERENCE = "def reference(nums):\n    return max([0] + [sum(nums[i:j]) for i in range(len(nums)) for j in range(i + 1, len(nums) + 1)])\n"


def _set(tmp_path, reference: str):
    folder = tmp_path / "max-subarray"
    folder.mkdir()
    (folder / "statement.txt").write_text(STATEMENT, encoding="utf-8")
    (folder / "reference.py").write_text(reference, encoding="utf-8")
    (folder / "meta.json").write_text(json.dumps({"category": "dp"}), encoding="utf-8")
    (tmp_path / "notes").mkdir()  # folders without a statement are ignored
    return tmp_path


def _run(tmp_path, reference: str):
    ai = AIClient({r: "fake:test" for r in ROLES}, fake=happy())
    return run_eval(_set(tmp_path, reference), ai, SandboxClient(SOCKET), token_limit=200_000,
                    max_repairs=2, log=lambda *_: None)  # fmt: skip


@pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")
def test_eval_reports_from_real_runs(tmp_path):
    summary, path = _run(tmp_path, REFERENCE)
    assert summary["problems"] == 1 and summary["all_verified_pct"] == 100.0
    assert summary["false_verifications"] == 0 and summary["integrity_failures"] == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    row = report["problems"][0]
    assert row["slug"] == "max-subarray" and row["tokens"] > 0 and row["seconds"] > 0
    md = path.with_suffix(".md").read_text(encoding="utf-8")
    assert "| **False verifications** | **0** |" in md
    assert STATEMENT not in path.read_text(encoding="utf-8")  # the report never holds the text


@pytest.mark.skipif(not SOCKET, reason="ALGOLENS_TEST_SANDBOX_SOCKET not set")
def test_eval_catches_a_false_verification(tmp_path):
    summary, path = _run(tmp_path, WRONG_REFERENCE)
    assert summary["false_verifications"] == 2  # both verified approaches disagree with it
    md = path.with_suffix(".md").read_text(encoding="utf-8")
    assert "## False verifications" in md and "⚠ false verification" in md


def test_summary_numbers():
    rows = [
        {"slug": "a", "status": "done", "seconds": 10, "tokens": 100, "approaches": [
            {"name": "B", "is_brute": True, "status": "verified", "reason": ""},
            {"name": "K", "is_brute": False, "status": "verified", "reason": ""}]},
        {"slug": "b", "status": "done", "seconds": 30, "tokens": 300, "ab_disagreement": True,
         "approaches": [
            {"name": "B", "is_brute": True, "status": "unverified",
             "reason": "The two independent reference solutions disagree on input [1]"},
            {"name": "K", "is_brute": False, "status": "unverified",
             "reason": "The two independent reference solutions disagree on input [2]"}]},
        {"slug": "c", "status": "rejected", "reason": "This is a geometry proof.", "seconds": 2,
         "tokens": 50},
    ]  # fmt: skip
    s = summarize(rows)
    assert s["problems"] == 3 and s["all_verified_pct"] == 33.3 and s["any_verified_pct"] == 33.3
    assert s["non_brute_verified_pct"] == 33.3 and s["none_verified_pct"] == 66.7
    assert s["ab_disagreements"] == 1 and s["rejected"] == 1
    assert s["seconds"]["median"] == 10 and s["tokens"]["max"] == 300
    assert s["reasons"]["The two independent reference solutions disagree"] == 2
