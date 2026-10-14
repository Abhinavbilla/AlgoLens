"""Verify library entries the way generated approaches are verified (spec: "Library entries
have to be verified like everything else").

For each entry:
1. The tests: the hand-written ones, plus RANDOM_TESTS random inputs generated from the
   entry's input schema (and its validator, if any). Every hand-written test and the
   default input must satisfy the input rules too.
2. The Python solution agrees with the independent reference on every test.
3. The C++ solution gives the same output as the Python one on every test.
4. Recording doesn't change the result on any test input (traced vs untraced, all in the
   sandbox), and the default input records within the 300-frame limit.
5. The narration lints clean on the recordings of the default input and hand-written tests:
   no ungrounded numbers, and no two templates that apply to one step but say different things.

A sandbox fault raises SandboxUnavailable and records nothing: it's never a verdict.
"""

import hashlib
from datetime import UTC, datetime

from algolens.animation.builder import AnimationError, before_view, build, compile_visual
from algolens.animation.values import FrameView
from algolens.library.loader import EntrySource
from algolens.narration.engine import compile_templates, lint
from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.generate import GenerationError
from algolens.schema.service import check_input, generate_tests

RANDOM_TESTS = 300


def seed_for(slug: str) -> int:
    return int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)


def verify_entry(entry: EntrySource, client: SandboxClient) -> dict:
    failures: list[str] = []
    rules = entry.rules()

    named = [("default input", entry.default_input)] + [
        (f"hand-written test {i}", t) for i, t in enumerate(entry.tests)
    ]
    for name, inp in named:
        issues = check_input(rules, inp["args"], client)
        if issues:
            failures.append(f"{name} breaks the input rules: {issues[0]}")
    try:
        random_inputs = generate_tests(rules, RANDOM_TESTS, seed_for(entry.slug), client)
    except GenerationError as exc:
        random_inputs = []
        failures.append(f"couldn't generate random tests: {exc}")
    inputs = [t["args"] for t in entry.tests] + random_inputs
    labels = [f"hand-written test {i}" for i in range(len(entry.tests))] + [
        f"random test {i}" for i in range(len(random_inputs))
    ]
    tests = [{"id": f"t{i}", "input": {"args": a}} for i, a in enumerate(inputs)]

    extras = entry.sandbox_extras()  # which arguments become TreeNode / ListNode
    py = _batch(client, "python", entry.python_code, entry.entry, tests, extras)
    ref = _batch(client, "python", entry.reference_code, "reference", tests, extras)
    cpp = _batch(client, "cpp", entry.cpp_code, "", tests, {})
    for label, args, p, r, c in zip(labels, inputs, py, ref, cpp, strict=True):
        if r["outcome"] != "ok":
            failures.append(f"{label} {args}: reference failed ({r['outcome']}: {r['detail']})")
            continue
        if p["outcome"] != "ok" or p["value"] != r["value"]:
            failures.append(f"{label} {args}: python gave {_show(p)}, reference {r['value']!r}")
        if c["outcome"] != "ok" or c["value"] != p.get("value"):
            failures.append(f"{label} {args}: c++ gave {_show(c)}, python {p.get('value')!r}")

    # Recording integrity on every input.
    all_inputs = [entry.default_input] + [{"args": a} for a in inputs]
    check = client.trace_check(
        {"source": entry.python_code, "entry": entry.entry, "inputs": all_inputs, **extras}
    )
    if check["status"] == "sandbox_error":
        raise SandboxUnavailable(check.get("detail", "sandbox error while checking recordings"))
    if check["status"] != "ok":
        failures.append(
            f"recording check didn't finish: {check['status']} {check.get('detail', '')}"
        )
    for label, res in zip(["default input"] + labels, check.get("results", []), strict=False):
        if res["status"] == "trace_failed" and label != "default input":
            continue  # too big to record is fine for a test: it just isn't animated
        if res["status"] != "ok":
            failures.append(f"{label}: recording {res['status']} {res.get('detail', '')}".strip())

    # The default animation builds, and the narration lints clean on full recordings.
    templates = compile_templates(entry.narration)
    panels = compile_visual(entry.visual)
    views, befores = [], []
    for name, inp in [("default input", entry.default_input)] + [
        (f"hand-written test {i}", t) for i, t in enumerate(entry.tests)
    ]:
        resp = client.trace(
            {"source": entry.python_code, "entry": entry.entry, "input": inp, **extras}
        )
        if resp["status"] == "sandbox_error":
            raise SandboxUnavailable(resp.get("detail", "sandbox error while tracing"))
        if resp["status"] != "ok":
            if name == "default input":
                failures.append(f"{name}: recording failed ({resp['status']})")
            continue
        trace = resp["trace"]
        if name == "default input":
            try:
                build(trace, source=entry.python_code, templates=templates, panels=panels,
                      cpp_lines=entry.cpp_line_map())  # fmt: skip
            except AnimationError as exc:
                failures.append(f"default input: {exc}")
        frame_views = [FrameView(f, trace["heap"]) for f in trace["frames"]]
        views += frame_views
        befores += [before_view(frame_views[i - 1] if i else None, v)
                    for i, v in enumerate(frame_views)]  # fmt: skip
    narration = lint(templates, views, befores)
    failures += [f"narration: {e}" for e in narration["errors"]]

    n_hand, n_random = len(entry.tests), len(random_inputs)
    return {
        "status": "verified" if not failures else "failed",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "content_hash": entry.content_hash,
        "method": f"{n_hand} hand-written and {n_random} random tests",
        "tests": n_hand + n_random,
        "random_tests": n_random,
        "failures": failures[:50],
        "narration": {"coverage": narration["coverage"], "warnings": narration["warnings"]},
    }


TIME_DEPENDENT = ("timeout", "not_run")


def _batch(
    client: SandboxClient, language: str, source: str, entry: str, tests: list, extras: dict
) -> list:
    """Results for every test. A test that timed out (or didn't get to run because the batch
    ran out of time) is retried once on its own before it counts: on a busy machine the wall
    clock can run out for code that's fine, and that must never look like a wrong answer.
    A repeated timeout is reported as a timeout, not as a wrong output."""
    results = _run_batch(client, language, source, entry, tests, extras, wall_s=240)
    if results and all(r["outcome"] == "compile_timeout" for r in results):
        results = _run_batch(client, language, source, entry, tests, extras, wall_s=240)
    retry = [i for i, r in enumerate(results) if r["outcome"] in TIME_DEPENDENT]
    if retry and len(retry) <= 50:
        again = _run_batch(
            client, language, source, entry, [tests[i] for i in retry], extras, wall_s=120
        )
        for i, r in zip(retry, again, strict=True):
            results[i] = r
    return results


def _run_batch(client, language, source, entry, tests, extras: dict, wall_s: int) -> list:
    resp = client.run_batch({
        "language": language, "source": source, "entry": entry, "tests": tests, **extras,
        "batch_wall_s": wall_s,
    })  # fmt: skip
    if resp["status"] == "sandbox_error":
        raise SandboxUnavailable(resp.get("detail", "sandbox error"))
    if resp["status"] in ("compile_error", "compile_timeout"):  # every test fails
        detail = resp.get("compile_output") or resp.get("detail", "")
        return [{"outcome": resp["status"], "detail": detail[-300:], "value": None}] * len(tests)
    # ok or batch_timeout: finished tests keep their results, the rest are "not_run"
    return list(resp["results"])


def _show(result: dict) -> str:
    if result["outcome"] == "ok":
        return repr(result["value"])
    return f"{result['outcome']} ({result.get('detail', '')})"
