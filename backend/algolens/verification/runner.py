"""Running code on many tests in the sandbox, shared by library and problem verification.

Time-dependent results are retried before they count (plan §6.1, rule 8): a test that timed
out or didn't get to run is retried once on its own, and a compile timeout reruns the batch.
A repeat is reported as a timeout, never as a wrong answer. A sandbox fault raises
SandboxUnavailable: no verdict is ever drawn from it.
"""

from algolens.sandbox.client import SandboxClient, SandboxUnavailable

TIME_DEPENDENT = ("timeout", "not_run")
CHUNK = 100  # tests per sandbox batch (lets progress be reported between batches)


def run_tests(
    client: SandboxClient, language: str, source: str, entry: str, tests: list, extras: dict,
    on_progress=None, per_test: dict | None = None,
) -> list[dict]:  # fmt: skip
    """One result per test ({"outcome", "value", "detail"}, plus "ops" for tests that ask
    for a count), in order. `per_test` overrides the sandbox's per-test limits."""
    if per_test:
        extras = {**extras, "per_test": per_test}
    out: list[dict] = []
    for i in range(0, len(tests), CHUNK):
        chunk = tests[i : i + CHUNK]
        out += _batch(client, language, source, entry, chunk, extras)
        if on_progress:
            on_progress(len(out))
    return out


def _batch(client, language, source, entry, tests, extras) -> list[dict]:
    results = _run_batch(client, language, source, entry, tests, extras, wall_s=240)
    if results and all(r["outcome"] == "compile_timeout" for r in results):
        results = _run_batch(client, language, source, entry, tests, extras, wall_s=240)
    retry = [i for i, r in enumerate(results) if r["outcome"] in TIME_DEPENDENT]
    if retry and len(retry) <= 50:
        again = _run_batch(client, language, source, entry, [tests[i] for i in retry], extras, 120)
        for i, r in zip(retry, again, strict=True):
            results[i] = r
    broken = next((r for r in results if r["outcome"] == "setup_error"), None)
    if broken:  # the jail couldn't be set up for a test: our fault, not the code's
        raise SandboxUnavailable(f"test setup failed: {broken.get('detail', '')[:200]}")
    return results


def _run_batch(client, language, source, entry, tests, extras, wall_s: int) -> list[dict]:
    resp = client.run_batch({
        "language": language, "source": source, "entry": entry, "tests": tests,
        "batch_wall_s": wall_s, **extras,
    })  # fmt: skip
    if resp["status"] == "sandbox_error":
        raise SandboxUnavailable(resp.get("detail", "sandbox error"))
    if resp["status"] in ("compile_error", "compile_timeout"):
        detail = resp.get("compile_output") or resp.get("detail", "")
        return [{"outcome": resp["status"], "detail": detail[-600:], "value": None}] * len(tests)
    return list(resp["results"])  # ok or batch_timeout (unfinished tests are "not_run")


def show(result: dict) -> str:
    if result["outcome"] == "ok":
        return repr(result["value"])
    return f"{result['outcome']} ({result.get('detail', '')[:200]})"
