"""Verify library entries the way generated approaches are verified (spec: "Library entries
have to be verified like everything else").

For each entry:
1. The Python solution agrees with the independent reference on every test.
2. The C++ solution gives the same output as the Python one on every test.
3. Recording doesn't change the result on any test input (the sandbox compares traced and
   untraced runs), and the default input records within the 300-frame limit.
4. The narration lints clean on every recorded frame: no ungrounded numbers, and no two
   templates that apply to the same step but say different things.

Random tests from the input schema join in M3; until then the hand-written tests are used.
A sandbox fault raises SandboxUnavailable and records nothing: it's never a verdict.
"""

from datetime import UTC, datetime

from algolens.animation.builder import AnimationError, before_view, build, compile_visual
from algolens.animation.values import FrameView
from algolens.library.loader import EntrySource
from algolens.narration.engine import compile_templates, lint
from algolens.sandbox.client import SandboxClient, SandboxUnavailable

METHOD = "hand-written tests; random tests arrive with the input schema (M3)"


def verify_entry(entry: EntrySource, client: SandboxClient) -> dict:
    failures: list[str] = []
    tests = [{"id": f"t{i}", "input": inp} for i, inp in enumerate(entry.tests)]

    py = _batch(client, "python", entry.python_code, entry.entry, tests)
    ref = _batch(client, "python", entry.reference_code, "reference", tests)
    cpp = _batch(client, "cpp", entry.cpp_code, "", tests)
    for i, (p, r, c) in enumerate(zip(py, ref, cpp, strict=True)):
        if r["outcome"] != "ok":
            failures.append(f"test {i}: reference failed ({r['outcome']}: {r['detail']})")
            continue
        if p["outcome"] != "ok" or p["value"] != r["value"]:
            failures.append(f"test {i}: python gave {_show(p)}, reference {r['value']!r}")
        if c["outcome"] != "ok" or c["value"] != p.get("value"):
            failures.append(f"test {i}: c++ gave {_show(c)}, python {p.get('value')!r}")

    templates = compile_templates(entry.narration)
    panels = compile_visual(entry.visual)
    views, befores = [], []
    inputs = [("default", entry.default_input)] + [
        (f"test {i}", t) for i, t in enumerate(entry.tests)
    ]
    for name, args_input in inputs:
        resp = client.trace(
            {"source": entry.python_code, "entry": entry.entry, "input": args_input}
        )
        status = resp["status"]
        if status == "sandbox_error":
            raise SandboxUnavailable(resp.get("detail", "sandbox error while tracing"))
        if status == "trace_failed" and name != "default":
            continue  # too big to record is fine for a test input; it just isn't animated
        if status != "ok":
            failures.append(f"{name}: recording failed ({status}: {resp.get('detail', '')})")
            continue
        trace = resp["trace"]
        if name == "default":
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
    return {
        "status": "verified" if not failures else "failed",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "content_hash": entry.content_hash,
        "method": METHOD,
        "tests": len(tests),
        "failures": failures,
        "narration": {"coverage": narration["coverage"], "warnings": narration["warnings"]},
    }


def _batch(client: SandboxClient, language: str, source: str, entry: str, tests: list) -> list:
    resp = client.run_batch(
        {"language": language, "source": source, "entry": entry, "tests": tests}
    )
    if resp["status"] == "sandbox_error":
        raise SandboxUnavailable(resp.get("detail", "sandbox error"))
    if resp["status"] != "ok":  # compile error or batch timeout: every test fails
        detail = resp.get("compile_output") or resp.get("detail", "")
        return [{"outcome": resp["status"], "detail": detail[-300:], "value": None}] * len(tests)
    return resp["results"]


def _show(result: dict) -> str:
    if result["outcome"] == "ok":
        return repr(result["value"])
    return f"{result['outcome']} ({result.get('detail', '')})"
