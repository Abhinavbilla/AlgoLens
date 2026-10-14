"""`algolens eval`: run the full pipeline on a local problem set and report (plan §10).

Eval set layout (stays on your machine; /eval/ is git-ignored):

    eval/<slug>/statement.txt   the problem as you'd paste it
    eval/<slug>/reference.py    defines reference(*args): an accepted solution, taking the
                                arguments in the parsed signature's order. It may also define
                                check(*args, output) -> bool for problems with many valid
                                answers; then that decides correctness.
    eval/<slug>/meta.json       {"category": "...", "tags": ["checker", ...],
                                 "param_names": ["nums", "k"]}  (optional: if the parsed
                                 names differ in order, arguments are reordered by name)

For each problem the pipeline runs without the cache. Then:
- criterion 2: every verified approach is run against reference.py on 300 fresh random inputs
  (a different seed from verification). Any disagreement is a false verification.
- criterion 3: each animated approach's default input is recorded again; the recording must
  match the untraced run, and the animation must build with every frame's narration grounded.
Every number in the report comes straight from these runs.
"""

import hashlib
import json
import statistics
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algolens.ai.budget import Budget
from algolens.ai.client import AIClient, AIError
from algolens.animation.builder import AnimationError
from algolens.animation.service import TraceFailed, animate
from algolens.pipeline.service import input_rules
from algolens.pipeline.solve import RANDOM_TESTS, SolveResult, solve
from algolens.pipeline.visualize import AnimationSource, sandbox_extras
from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.generate import GenerationError
from algolens.schema.service import generate_tests
from algolens.verification.compare import same
from algolens.verification.runner import run_tests, show

EVAL_SEED_SALT = "algolens-eval"


def load_set(root: Path, only: list[str] | None = None) -> list[dict]:
    problems = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "reports"):
        if only and folder.name not in only:
            continue
        statement, reference = folder / "statement.txt", folder / "reference.py"
        if not statement.exists() or not reference.exists():
            continue
        meta_path = folder / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        problems.append(
            {
                "slug": folder.name,
                "statement": statement.read_text(encoding="utf-8"),
                "reference": reference.read_text(encoding="utf-8"),
                "meta": meta,
            }
        )
    return problems


def evaluate_problem(
    p: dict, ai: AIClient, sandbox: SandboxClient, token_limit: int, max_repairs: int
) -> dict:
    out: dict[str, Any] = {
        "slug": p["slug"],
        "category": p["meta"].get("category", ""),
        "tags": p["meta"].get("tags", []),
    }
    budget = Budget(token_limit)
    started = time.monotonic()
    try:
        result = solve(p["statement"], ai, sandbox, budget, max_repairs=max_repairs)
    except (SandboxUnavailable, AIError) as exc:
        out.update(
            status="error",
            error=f"{type(exc).__name__}: {exc}",
            seconds=round(time.monotonic() - started, 1),
            tokens=budget.report()["used"],
        )
        return out
    out["seconds"] = round(time.monotonic() - started, 1)
    out["tokens"] = result.tokens.get("used", 0)
    out["status"] = result.status
    out["reason"] = result.reason
    out["failures"] = result.failures
    out["budget_exhausted"] = (
        any("budget" in f for f in result.failures) or "budget" in result.reason
    )
    out["ab_disagreement"] = any("disagree" in f and "independent" in f for f in result.failures)
    out["approaches"] = [
        {
            "name": a.name,
            "is_brute": a.is_brute,
            "status": a.status,
            "reason": a.reason,
            "repairs": a.repairs,
        }
        for a in result.approaches
    ]
    if result.status == "done":
        out["false_verifications"] = _cross_check(p, result, sandbox)
        out["integrity_failures"] = _integrity(result, sandbox)
    return out


def _reference_args(p: dict, spec: dict, args: list) -> list:
    names = p["meta"].get("param_names")
    parsed = [q["name"] for q in spec.get("params", [])]
    if names and sorted(names) == sorted(parsed):
        by_name = dict(zip(parsed, args, strict=True))
        return [by_name[n] for n in names]
    return args


def _cross_check(p: dict, result: SolveResult, sandbox: SandboxClient) -> list[dict]:
    spec = result.spec or {}
    verified = [a for a in result.approaches if a.status == "verified"]
    if not verified:
        return []
    seed = int(hashlib.sha256((EVAL_SEED_SALT + p["statement"]).encode()).hexdigest()[:8], 16)
    try:
        inputs = generate_tests(input_rules(spec), RANDOM_TESTS, seed, sandbox)
    except GenerationError as exc:
        return [{"approach": "*", "detail": f"couldn't generate fresh inputs: {exc}"}]
    extras = sandbox_extras(spec)
    ref_tests = [
        {"id": f"r{i}", "input": {"args": _reference_args(p, spec, a)}}
        for i, a in enumerate(inputs)
    ]
    ref = run_tests(sandbox, "python", p["reference"], "reference", ref_tests, extras)
    has_check = "def check(" in p["reference"]
    tests = [{"id": f"t{i}", "input": {"args": a}} for i, a in enumerate(inputs)]
    kind = (spec.get("comparator") or {}).get("kind", "exact")
    tol = (spec.get("comparator") or {}).get("tolerance", 1e-6)
    out = []
    for a in verified:
        got = run_tests(sandbox, "python", a.python_code, spec["function_name"], tests, extras)
        if has_check:
            pairs = [
                {"id": f"c{i}", "input": {"args": [*_reference_args(p, spec, x), g.get("value")]}}
                for i, (x, g) in enumerate(zip(inputs, got, strict=True))
            ]
            convert = extras.get("convert")
            verdicts = run_tests(
                sandbox,
                "python",
                p["reference"],
                "check",
                pairs,
                {"convert": [*convert, None]} if convert else {},
            )
            bad = next(
                (
                    i
                    for i, (g, v) in enumerate(zip(got, verdicts, strict=True))
                    if g["outcome"] != "ok" or v.get("value") is not True
                ),
                None,
            )
        else:

            def wrong(r: dict, g: dict) -> bool:
                if r["outcome"] != "ok":
                    return False  # the reference couldn't answer: no evidence either way
                if g["outcome"] != "ok":
                    return True
                return not same("exact" if kind == "checker" else kind, r["value"], g["value"], tol)

            bad = next(
                (i for i, (r, g) in enumerate(zip(ref, got, strict=True)) if wrong(r, g)), None
            )
        if bad is not None:
            out.append(
                {
                    "approach": a.name,
                    "input": inputs[bad],
                    "expected": ref[bad].get("value"),
                    "got": show(got[bad]),
                }
            )
    return out


def _integrity(result: SolveResult, sandbox: SandboxClient) -> list[dict]:
    spec = result.spec or {}
    failures = []
    for a in result.approaches:
        plan = a.animation
        if not plan or "unavailable" in plan:
            continue
        source = AnimationSource(
            a.name, spec["function_name"], a.python_code, sandbox_extras(spec), plan
        )
        try:
            animation = animate(source, plan["default_input"], sandbox)
        except (TraceFailed, AnimationError) as exc:
            failures.append({"approach": a.name, "detail": str(exc)})
            continue
        ungrounded = [f["i"] for f in animation["frames"] if not f["narration"]["text"]]
        if ungrounded:
            failures.append(
                {"approach": a.name, "detail": f"frames without narration: {ungrounded[:10]}"}
            )
    return failures


# --- report ----------------------------------------------------------------------------------


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def _quantiles(xs: list[float]) -> dict:
    if not xs:
        return {"median": None, "p90": None, "max": None}
    xs = sorted(xs)
    p90 = xs[min(len(xs) - 1, int(round(0.9 * (len(xs) - 1))))]
    return {"median": statistics.median(xs), "p90": p90, "max": xs[-1]}


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    done = [r for r in rows if r.get("status") == "done"]

    def statuses(r: dict) -> list[str]:
        return [a["status"] for a in r.get("approaches", [])]

    reasons = Counter()
    for r in rows:
        if r.get("status") in ("rejected", "failed", "error"):
            reasons[_reason_key(r.get("reason") or r.get("error", ""))] += 1
        for a in r.get("approaches", []):
            if a["status"] != "verified" and a["reason"]:
                reasons[_reason_key(a["reason"])] += 1
    return {
        "problems": n,
        "all_verified_pct": _pct(
            sum(bool(statuses(r)) and all(s == "verified" for s in statuses(r)) for r in done), n
        ),
        "any_verified_pct": _pct(sum("verified" in statuses(r) for r in done), n),
        "non_brute_verified_pct": _pct(
            sum(
                any(
                    a["status"] == "verified" and not a["is_brute"] for a in r.get("approaches", [])
                )
                for r in done
            ),
            n,
        ),
        "none_verified_pct": _pct(sum("verified" not in statuses(r) for r in rows), n),
        "any_timeout_pct": _pct(sum("timeout" in statuses(r) for r in done), n),
        "rejected": sum(r.get("status") == "rejected" for r in rows),
        "errors": sum(r.get("status") == "error" for r in rows),
        "seconds": _quantiles([r["seconds"] for r in rows if "seconds" in r]),
        "tokens": _quantiles([r["tokens"] for r in rows if "tokens" in r]),
        "budget_exhaustions": sum(bool(r.get("budget_exhausted")) for r in rows),
        "ab_disagreements": sum(bool(r.get("ab_disagreement")) for r in rows),
        "false_verifications": sum(len(r.get("false_verifications", [])) for r in rows),
        "integrity_failures": sum(len(r.get("integrity_failures", [])) for r in rows),
        "reasons": dict(reasons.most_common()),
    }


def _reason_key(reason: str) -> str:
    """Group reasons by their kind, not their specific input."""
    for marker in (" on input ", " on a valid input ", ": input ", " (", ":"):
        if marker in reason:
            reason = reason.split(marker)[0]
    return reason.strip()[:120] or "unknown"


def render_markdown(summary: dict, rows: list[dict], started: str) -> str:
    s = summary
    lines = [
        f"# AlgoLens eval, {started}",
        "",
        f"Problems: **{s['problems']}** (rejected {s['rejected']}, errors {s['errors']})",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| All approaches verified | {s['all_verified_pct']}% |",
        f"| At least one verified | {s['any_verified_pct']}% |",
        f"| At least one verified non-brute approach | {s['non_brute_verified_pct']}% |",
        f"| Nothing verified | {s['none_verified_pct']}% |",
        f"| Some approach timed out | {s['any_timeout_pct']}% |",
        f"| Time per problem (s): median / p90 / max | {s['seconds']['median']} / "
        f"{s['seconds']['p90']} / {s['seconds']['max']} |",
        f"| Tokens per problem: median / p90 / max | {s['tokens']['median']} / "
        f"{s['tokens']['p90']} / {s['tokens']['max']} |",
        f"| Budget exhaustions | {s['budget_exhaustions']} |",
        f"| Brute A/B disagreements | {s['ab_disagreements']} |",
        f"| **False verifications** | **{s['false_verifications']}** |",
        f"| Frame-integrity failures | {s['integrity_failures']} |",
        "",
        "## Reasons",
        "",
    ]
    lines += [f"- {count} × {reason}" for reason, count in s["reasons"].items()] or ["- none"]
    lines += [
        "",
        "## Problems",
        "",
        "| Problem | Status | Approaches | Time (s) | Tokens |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        approaches = ", ".join(f"{a['name']}: {a['status']}" for a in r.get("approaches", []))
        status = r.get("status", "")
        if r.get("false_verifications"):
            status += " ⚠ false verification"
        lines.append(
            f"| {r['slug']} | {status} | {approaches or r.get('reason') or r.get('error', '')} "
            f"| {r.get('seconds', '')} | {r.get('tokens', '')} |"
        )
    false = [(r["slug"], f) for r in rows for f in r.get("false_verifications", [])]
    if false:
        lines += ["", "## False verifications", ""]
        lines += [
            f"- {slug} / {f['approach']}: input `{json.dumps(f.get('input'))}` expected "
            f"`{json.dumps(f.get('expected'))}`, got `{f.get('got', f.get('detail'))}`"
            for slug, f in false
        ]
    return "\n".join(lines) + "\n"


def run_eval(
    set_dir: Path,
    ai: AIClient,
    sandbox: SandboxClient,
    *,
    token_limit: int,
    max_repairs: int,
    only: list[str] | None = None,
    log=print,
) -> tuple[dict, Path]:
    problems = load_set(set_dir, only)
    if not problems:
        raise SystemExit(
            f"no problems found in {set_dir} (each needs statement.txt and reference.py)"
        )
    started = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rows = []
    for i, p in enumerate(problems, 1):
        log(f"[{i}/{len(problems)}] {p['slug']} …")
        row = evaluate_problem(p, ai, sandbox, token_limit, max_repairs)
        rows.append(row)
        log(
            f"    {row.get('status')}: "
            + ", ".join(f"{a['name']} {a['status']}" for a in row.get("approaches", []))
            + (f" ({row.get('reason') or row.get('error')})" if row.get("status") != "done" else "")
        )
    summary = summarize(rows)
    reports = set_dir / "reports"
    reports.mkdir(exist_ok=True)
    path = reports / f"{started}.json"
    path.write_text(
        json.dumps(
            {"started": started, "summary": summary, "problems": rows}, indent=2, default=str
        ),
        encoding="utf-8",
    )
    (reports / f"{started}.md").write_text(
        render_markdown(summary, rows, started), encoding="utf-8"
    )
    return summary, path
