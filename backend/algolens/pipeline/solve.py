"""From a pasted statement to verified approaches (plan §6).

An approach is verified only if (spec, "What verified means"):
1. it gives the expected output on every worked example,
2. it agrees with the brute force on at least 300 random valid inputs, and
3. its C++ version gives the same outputs as its Python version on those inputs.
The brute force itself is verified by the examples, its Python/C++ match, and agreement with
a second, independent brute force (Brute B) on every random input.

Nothing here turns a failure of our own machinery into a verdict: sandbox faults and AI
outages raise (the job ends with an error), time-dependent results are retried and reported
as timeouts, and running out of token budget leaves unfinished approaches unverified with
that reason.
"""

import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from algolens.ai.budget import Budget, BudgetExhausted
from algolens.ai.client import AIClient, AIError
from algolens.pipeline import prompts
from algolens.pipeline.models import (
    ApproachList,
    BruteB,
    Checker,
    GeneratedApproach,
    ParsedProblem,
)
from algolens.sandbox.client import SandboxClient
from algolens.schema.generate import GenerationError
from algolens.schema.model import SchemaError, compile_schema
from algolens.schema.service import InputRules, all_inputs, check_input, generate_tests
from algolens.verification.compare import same
from algolens.verification.runner import run_tests, show

RANDOM_TESTS = 300
MUTATION_SAMPLE = 40
MIN_MUTATIONS_REJECTED = 0.7
SLOW = ("timeout", "not_run")

Progress = Callable[[str, int, int], None]


class Rejected(Exception):
    """The statement is out of scope, not DSA, or couldn't be pinned down."""


class BadReply(AIError):
    """The model twice returned JSON that doesn't fit the role's required shape."""


@dataclass
class ApproachResult:
    name: str
    key_idea: str
    time: str
    space: str
    python_code: str
    cpp_code: str
    is_brute: bool
    status: str = "unverified"  # verified | unverified | timeout
    reason: str = ""
    tests_passed: int = 0
    tests_total: int = 0
    examples_checked: int = 0
    repairs: int = 0
    repair_reasons: list[str] = field(default_factory=list)  # why each repair was needed
    exhaustive: bool = False  # the tests covered every valid input (fewer than 300 exist)
    failing_case: dict | None = None
    animation: dict | None = None  # see pipeline/visualize.py; only for verified approaches

    def public(self) -> dict:
        return asdict(self)


@dataclass
class SolveResult:
    status: str  # done | rejected | failed
    reason: str = ""
    spec: dict | None = None
    approaches: list[ApproachResult] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    explanation: dict | None = None  # the thought process; see _explain()


class _Run:
    def __init__(
        self,
        text: str,
        ai: AIClient,
        sandbox: SandboxClient,
        budget: Budget,
        progress: Progress | None,
        max_repairs: int,
    ):
        self.text = text
        self.ai = ai
        self.sandbox = sandbox
        self.budget = budget
        self.progress = progress or (lambda stage, done=0, total=0: None)
        self.max_repairs = max_repairs
        self.timings: dict[str, float] = {}
        self.failures: list[str] = []

    def timed(self, stage: str):
        run = self

        class _T:
            def __enter__(self):
                self.t = time.monotonic()
                run.progress(stage, 0, 0)

            def __exit__(self, *exc):
                spent = run.timings.get(stage, 0) + time.monotonic() - self.t
                run.timings[stage] = round(spent, 2)

        return _T()

    def ask(self, role: str, system: str, prompt: str, model: type[BaseModel]) -> Any:
        """One AI call whose reply must fit `model`; asked once more with the error if not."""
        reply = self.ai.complete_json(role, system, prompt, self.budget)
        try:
            return model.model_validate(reply.data)
        except ValidationError as exc:
            retry = (
                f"{prompt}\n\nYour previous reply didn't fit the required shape:\n"
                f"{str(exc)[:1500]}\nReply again with the corrected JSON object."
            )
            again = self.ai.complete_json(role, system, retry, self.budget)
            try:
                return model.model_validate(again.data)
            except ValidationError as exc2:
                raise BadReply(f"{role}: reply didn't fit the required shape: {exc2}") from exc2

    def parse(self) -> tuple[ParsedProblem, InputRules]:
        problem = ""
        for _ in range(2):
            try:
                spec = self.ask(
                    "parse", prompts.PARSE_SYSTEM, prompts.parse_prompt(self.text, problem),
                    ParsedProblem,
                )  # fmt: skip
            except BadReply as exc:
                problem = str(exc)[:800]
                continue
            if not spec.in_scope:
                raise Rejected(spec.rejection_reason or "This isn't a problem AlgoLens supports.")
            problem = self._check_spec(spec)
            if not problem:
                schema = compile_schema(spec.schema_json())
                return spec, InputRules(schema, spec.extra_rules_python or None)
        raise Rejected(
            "We couldn't read this problem reliably, so nothing was run. Try pasting it again, "
            f"perhaps with the examples written out clearly. (Details: {problem})"
        )

    def _check_spec(self, spec: ParsedProblem) -> str:
        if not spec.function_name or not spec.params:
            return "it needs a function name and at least one parameter"
        if not spec.examples:
            return "the statement needs at least one worked example"
        try:
            schema = compile_schema(spec.schema_json())
        except SchemaError as exc:
            return f"the input schema is invalid: {exc}"
        rules = InputRules(schema, spec.extra_rules_python or None)
        for i, ex in enumerate(spec.examples):
            issues = check_input(rules, ex.args, self.sandbox)
            if issues:
                return f"worked example {i + 1} doesn't fit the input schema: {issues[0]}"
        return ""


def solve(
    text: str,
    ai: AIClient,
    sandbox: SandboxClient,
    budget: Budget,
    progress: Progress | None = None,
    max_repairs: int = 2,
) -> SolveResult:
    """Raises SandboxUnavailable / AIError when our own machinery fails: never a verdict."""
    run = _Run(text, ai, sandbox, budget, progress, max_repairs)
    try:
        with run.timed("reading the problem"):
            spec, rules = run.parse()
    except Rejected as exc:
        return SolveResult("rejected", str(exc), timings=run.timings, tokens=budget.report())
    except BudgetExhausted as exc:
        return SolveResult(
            "failed", f"Ran out of AI budget while reading the problem ({exc}).",
            timings=run.timings, tokens=budget.report(),
        )  # fmt: skip
    result = SolveResult("done", spec=spec.model_dump(), timings=run.timings)
    try:
        _verify_all(run, spec, rules, result)
        _animate(run, result)
        _explain(run, result)
    except BudgetExhausted as exc:
        reason = f"Not verified: the problem's AI budget ran out ({exc})."
        run.failures.append(reason)
        if not result.approaches:
            result.status, result.reason = "failed", reason
        for a in result.approaches:
            if a.status != "verified" and not a.reason:
                a.reason = reason
    result.tokens = budget.report()
    result.failures = run.failures
    return result


def _verify_all(run: _Run, spec: ParsedProblem, rules: InputRules, result: SolveResult) -> None:
    sd = spec.model_dump()
    with run.timed("writing solutions"), ThreadPoolExecutor(max_workers=4) as pool:
        fut_a = pool.submit(
            run.ask, "brute_a", prompts.BRUTE_A_SYSTEM, prompts.brute_a_prompt(run.text, sd),
            GeneratedApproach,
        )  # fmt: skip
        fut_b = pool.submit(
            run.ask, "brute_b", prompts.BRUTE_B_SYSTEM, prompts.brute_b_prompt(run.text, sd),
            BruteB,
        )  # fmt: skip
        fut_x = pool.submit(
            run.ask, "approaches", prompts.APPROACHES_SYSTEM,
            prompts.approaches_prompt(run.text, sd), ApproachList,
        )  # fmt: skip
        fut_c = None
        if spec.comparator.kind == "checker":
            fut_c = pool.submit(
                run.ask, "checker", prompts.CHECKER_SYSTEM, prompts.checker_prompt(run.text, sd),
                Checker,
            )  # fmt: skip
        brute_a: GeneratedApproach = fut_a.result()
        brute_b: BruteB = fut_b.result()
        others: list[GeneratedApproach] = fut_x.result().approaches
        checker = fut_c.result().python_code if fut_c else None

    approaches = [ApproachResult(is_brute=True, **_fields(brute_a))]
    approaches += [ApproachResult(is_brute=False, **_fields(a)) for a in others]
    result.approaches = approaches

    with run.timed("building tests"):
        seed = int(hashlib.sha256(run.text.encode()).hexdigest()[:8], 16)
        exhaustive = False
        try:
            random_inputs = generate_tests(rules, RANDOM_TESTS, seed, run.sandbox)
        except GenerationError as exc:
            # Fewer than 300 distinct valid inputs exist (e.g. 1 <= n <= 45): test all of them.
            random_inputs = all_inputs(rules, RANDOM_TESTS, run.sandbox)
            exhaustive = random_inputs is not None
            if not exhaustive:
                reason = f"Couldn't generate valid random tests: {exc}"
                run.failures.append(reason)
                _fail_all(approaches, reason)
                return
        for a in approaches:
            a.exhaustive = exhaustive
    judge = _Judge(run, spec, checker, random_inputs, approaches)

    with run.timed("checking the brute force"):
        if not judge.check_brutes(approaches[0], brute_b):
            return
    for a in approaches[1:]:
        with run.timed(f"checking {a.name}"):
            judge.check_approach(a)


def _animate(run: _Run, result: SolveResult) -> None:
    """Animations only for verified code: an animation teaches, so it must be right."""
    from algolens.pipeline.visualize import plan_animation

    for a in result.approaches:
        if a.status != "verified":
            continue
        with run.timed("preparing animations"):
            try:
                a.animation = plan_animation(run, result.spec or {}, a.python_code, a.cpp_code)
            except BudgetExhausted:
                a.animation = {"unavailable": "The AI budget ran out before this was animated."}
                raise


def _explain(run: _Run, result: SolveResult) -> None:
    """The interview-style thought process, brute force to optimal, for the approaches that
    were verified (explaining unverified code would teach something that may be wrong). A
    reply that doesn't fit, or a provider error, leaves the page without it: the verified
    results stand on their own."""
    from algolens.pipeline.models import Explanation

    shown = [a for a in result.approaches if a.status == "verified"]
    if not shown:
        return
    with run.timed("writing the explanation"):
        try:
            reply = run.ask(
                "explain",
                prompts.EXPLAIN_SYSTEM,
                prompts.explain_prompt(run.text, result.spec or {}, [_fields(a) for a in shown]),
                Explanation,
            )
        except BudgetExhausted:
            raise
        except Exception as exc:  # AIError, a reply that never fit: no explanation, no failure
            run.failures.append(f"explanation unavailable: {str(exc)[:200]}")
            return
    if len(reply.approaches) != len(shown):
        run.failures.append("explanation unavailable: it didn't cover each approach once")
        return
    data = reply.model_dump()
    for a, thinking in zip(shown, data["approaches"], strict=True):
        thinking["name"] = a.name
        thinking["time"] = a.time
        thinking["space"] = a.space
        thinking["is_brute"] = a.is_brute
    result.explanation = data


def _fields(a: GeneratedApproach | ApproachResult) -> dict:
    keys = ("name", "key_idea", "time", "space", "python_code", "cpp_code")
    return {k: getattr(a, k) for k in keys}


def _fail_all(approaches: list[ApproachResult], reason: str) -> None:
    for a in approaches:
        a.status, a.reason = "unverified", reason


class _Judge:
    """Runs and compares solutions on the examples and the random tests.

    Comparisons are batched: with an AI-written checker, every answer that isn't identical to
    the known-good one goes to the sandbox in one batch rather than one call per test.
    """

    def __init__(
        self,
        run: _Run,
        spec: ParsedProblem,
        checker: str | None,
        random_inputs: list,
        approaches: list[ApproachResult],
    ):
        self.run = run
        self.spec = spec
        self.checker = checker
        self.approaches = approaches
        self.examples = spec.examples
        self.n_ex = len(spec.examples)
        self.inputs = [ex.args for ex in spec.examples] + random_inputs
        self.random = list(range(self.n_ex, len(self.inputs)))  # indices of the random tests
        self.tests = [{"id": f"t{i}", "input": {"args": a}} for i, a in enumerate(self.inputs)]
        self.extras: dict[str, Any] = {}
        convert = spec.convert()
        if any(convert):
            self.extras["convert"] = convert
        if spec.result_kind:
            self.extras["convert_result"] = spec.result_kind
        self.reference: list[dict] = []  # Brute A's outputs, once it's trusted

    # --- running and comparing -----------------------------------------------------------------

    def _python(self, code: str, label: str) -> list[dict]:
        total = len(self.tests)

        def progress(done: int) -> None:
            self.run.progress(f"checking {label}", done, total)

        return run_tests(
            self.run.sandbox, "python", code, self.spec.function_name, self.tests, self.extras,
            on_progress=progress,
        )  # fmt: skip

    def _cpp(self, code: str) -> list[dict]:
        return run_tests(self.run.sandbox, "cpp", code, "", self.tests, {})

    def _checked(self, pairs: list[tuple[list, Any]]) -> list[bool]:
        """Checker verdicts for (input, output) pairs; anything but True counts as rejected."""
        if not pairs:
            return []
        tests = [
            {"id": f"c{i}", "input": {"args": [*args, out]}} for i, (args, out) in enumerate(pairs)
        ]
        convert = self.extras.get("convert")
        extras = {"convert": [*convert, None]} if convert else {}
        res = run_tests(self.run.sandbox, "python", self.checker or "", "check", tests, extras)
        return [r["outcome"] == "ok" and r["value"] is True for r in res]

    def _accept(self, items: list[tuple[list, Any, Any]]) -> list[bool]:
        """For each (input, known-good answer, answer to judge): is the answer acceptable?"""
        kind, tol = self.spec.comparator.kind, self.spec.comparator.tolerance
        if kind != "checker":
            return [same(kind, good, got, tol) for _, good, got in items]
        out = [same("exact", good, got) for _, good, got in items]
        pending = [i for i, ok in enumerate(out) if not ok]
        verdicts = self._checked([(items[i][0], items[i][2]) for i in pending])
        for i, ok in zip(pending, verdicts, strict=True):
            out[i] = ok
        return out

    def _first_wrong(self, indices: list[int], results: list[dict], good: list[Any]) -> int | None:
        """The first of `indices` whose result isn't ok or isn't acceptable against good[i]."""
        ok = [i for i in indices if results[i]["outcome"] == "ok"]
        items = [(self.inputs[i], good[i], results[i]["value"]) for i in ok]
        accepted = {i for i, v in zip(ok, self._accept(items), strict=True) if v}
        return next((i for i in indices if i not in accepted), None)

    def _example_failure(self, results: list[dict]) -> str:
        expected = [ex.expected for ex in self.examples]
        i = self._first_wrong(list(range(self.n_ex)), results, expected)
        if i is None:
            return ""
        ex = self.examples[i]
        return (
            f"example {i + 1}: input {json.dumps(ex.args)} should give "
            f"{json.dumps(ex.expected)}, got {show(results[i])}"
        )

    def _no_reference(self, reason: str, case: dict | None = None) -> bool:
        """Without a trusted brute force nothing can be verified."""
        self.run.failures.append(reason)
        _fail_all(self.approaches, reason)
        for a in self.approaches:
            a.failing_case = case
        return False

    # --- brute forces ---------------------------------------------------------------------------

    def check_brutes(self, a: ApproachResult, brute_b: BruteB) -> bool:
        run, sd = self.run, self.spec.model_dump()
        res_a = self._python(a.python_code, "the brute force")
        fail = self._example_failure(res_a)
        if fail:  # regenerate once, told only which example it got wrong (plan §6.2)
            retry = prompts.brute_a_prompt(run.text, sd)
            retry += f"\n\nA previous attempt got this worked example wrong:\n{fail}\n"
            new = run.ask("brute_a", prompts.BRUTE_A_SYSTEM, retry, GeneratedApproach)
            for k, v in _fields(new).items():
                setattr(a, k, v)
            a.repairs += 1
            a.repair_reasons.append(fail[:500])
            res_a = self._python(a.python_code, "the brute force")
            fail = self._example_failure(res_a)
            if fail:
                return self._no_reference(f"The brute force got a worked example wrong ({fail}).")

        res_b = self._python(brute_b.python_code, "the second brute force")
        fail_b = self._example_failure(res_b)
        if fail_b:
            retry = prompts.brute_b_prompt(run.text, sd, fail_b)
            new_b = run.ask("brute_b", prompts.BRUTE_B_SYSTEM, retry, BruteB)
            res_b = self._python(new_b.python_code, "the second brute force")
            fail_b = self._example_failure(res_b)
            if fail_b:
                return self._no_reference(
                    f"The independent second brute force got a worked example wrong ({fail_b})."
                )

        # Both must finish every random input (they're small) and agree on all of them.
        for label, res in (("brute force", res_a), ("second brute force", res_b)):
            slow = [i for i in self.random if res[i]["outcome"] in SLOW]
            broken = [i for i in self.random if res[i]["outcome"] not in (*SLOW, "ok")]
            if broken:
                i = broken[0]
                return self._no_reference(
                    f"The {label} failed on a valid input {json.dumps(self.inputs[i])}: "
                    f"{show(res[i])}"
                )
            if slow:
                return self._no_reference(
                    f"The {label} was too slow to check against: it ran out of time on "
                    f"{len(slow)} of {len(self.random)} random inputs."
                )
        if self.checker:
            if not self._checker_is_sound(res_a, res_b):
                return False
            n = len(self.random)
            pairs = [(self.inputs[i], r[i]["value"]) for r in (res_a, res_b) for i in self.random]
            verdicts = self._checked(pairs)
            wrong = next((self.random[k] for k in range(n)
                          if not (verdicts[k] and verdicts[n + k])), None)  # fmt: skip
        else:
            wrong = self._first_wrong(self.random, res_b, [r["value"] for r in res_a])
        if wrong is not None:
            args, va, vb = self.inputs[wrong], res_a[wrong]["value"], res_b[wrong]["value"]
            return self._no_reference(
                f"The two independent reference solutions disagree on input {json.dumps(args)} "
                f"(first: {json.dumps(va)}, second: {json.dumps(vb)}), so nothing can be "
                "verified.",
                case={"input": args, "first": va, "second": vb},
            )
        self.reference = res_a

        # Brute A's own C++ must match its Python. Its Python is now the trusted reference, so a
        # repair may only replace the C++.
        a.examples_checked, a.tests_total = self.n_ex, len(self.random)
        mismatch = self._cpp_mismatch(res_a, self._cpp(a.cpp_code))
        for _ in range(run.max_repairs):
            if not mismatch:
                break
            prompt = prompts.repair_prompt(run.text, sd, _fields(a), mismatch[0])
            prompt += "\nKeep the Python exactly as it is (it is correct); fix only the C++.\n"
            new = run.ask("repair", prompts.REPAIR_SYSTEM, prompt, GeneratedApproach)
            a.cpp_code = new.cpp_code
            a.repairs += 1
            a.repair_reasons.append(mismatch[0][:500])
            mismatch = self._cpp_mismatch(res_a, self._cpp(a.cpp_code))
        if mismatch:
            a.status, a.reason, a.failing_case = "unverified", mismatch[0], mismatch[1]
        else:
            a.status, a.tests_passed = "verified", len(self.random)
        return True

    def _checker_is_sound(self, res_a: list[dict], res_b: list[dict]) -> bool:
        """Plan §6.5: the checker accepts the examples and both brute forces' outputs, and
        rejects most automatically mutated outputs. A checker that accepts anything is no
        better than no check, so then nothing can be verified."""
        sample = self.random[:MUTATION_SAMPLE]
        good = [(ex.args, ex.expected) for ex in self.examples]
        good += [(self.inputs[i], res[i]["value"]) for i in sample for res in (res_a, res_b)]
        if not all(self._checked(good)):
            return self._no_reference("The answer checker rejected a correct answer.")
        mutants = []
        for i in sample:
            m = mutate(res_a[i]["value"])
            if m is not None and m != res_a[i]["value"] and m != res_b[i]["value"]:
                mutants.append((self.inputs[i], m))
        if mutants:
            rejected = sum(not ok for ok in self._checked(mutants))
            if rejected / len(mutants) < MIN_MUTATIONS_REJECTED:
                return self._no_reference(
                    f"The answer checker is too lenient: it accepted {len(mutants) - rejected} of "
                    f"{len(mutants)} deliberately wrong answers, so it can't be trusted."
                )
        return True

    def _cpp_mismatch(self, py: list[dict], cpp: list[dict]) -> tuple[str, dict | None] | None:
        if cpp and cpp[0]["outcome"] == "compile_error":
            return f"The C++ version doesn't compile: {cpp[0]['detail'][:300]}", None
        if cpp and cpp[0]["outcome"] == "compile_timeout":
            return "The C++ version didn't compile in time (tried twice).", None
        idx = [i for i, p in enumerate(py) if p["outcome"] == "ok"]
        i = self._first_wrong(idx, cpp, [p["value"] for p in py])
        if i is None:
            return None
        args, pv = self.inputs[i], py[i]["value"]
        return (
            f"The C++ version disagrees with the Python version on input {json.dumps(args)}: "
            f"Python {json.dumps(pv)}, C++ {show(cpp[i])}",
            {"input": args, "python": pv, "cpp": cpp[i].get("value")},
        )

    # --- other approaches --------------------------------------------------------------------

    def check_approach(self, a: ApproachResult) -> None:
        for round_ in range(self.run.max_repairs + 1):
            problem = self._judge_approach(a)
            if problem is None:
                return
            reason, case, kind = problem
            if kind == "timeout" or round_ == self.run.max_repairs:
                a.status = "timeout" if kind == "timeout" else "unverified"
                a.reason, a.failing_case = reason, case
                return
            prompt = prompts.repair_prompt(
                self.run.text, self.spec.model_dump(), _fields(a), reason
            )
            new = self.run.ask("repair", prompts.REPAIR_SYSTEM, prompt, GeneratedApproach)
            for k, v in _fields(new).items():
                setattr(a, k, v)
            a.repairs += 1
            a.repair_reasons.append(reason[:500])

    def _judge_approach(self, a: ApproachResult) -> tuple[str, dict | None, str] | None:
        res = self._python(a.python_code, a.name)
        a.examples_checked, a.tests_total, a.tests_passed = self.n_ex, len(self.random), 0
        fail = self._example_failure(res)
        if fail:
            return f"Wrong on a worked example: {fail}", None, "wrong"
        i = self._first_wrong(self.random, res, [r["value"] for r in self.reference])
        if i is not None:
            args, ref, r = self.inputs[i], self.reference[i]["value"], res[i]
            if r["outcome"] in SLOW:
                return (
                    f"Too slow: ran out of time on input {json.dumps(args)}",
                    {"input": args},
                    "timeout",
                )
            return (
                f"Wrong on input {json.dumps(args)}: expected {json.dumps(ref)}, got {show(r)}",
                {"input": args, "expected": ref, "got": r.get("value")},
                "wrong",
            )
        a.tests_passed = len(self.random)
        mismatch = self._cpp_mismatch(res, self._cpp(a.cpp_code))
        if mismatch:
            return mismatch[0], mismatch[1], "wrong"
        a.status, a.reason, a.failing_case = "verified", "", None
        return None


def mutate(value: Any) -> Any:
    """A plausible-looking wrong answer, to test that the checker rejects it."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    if isinstance(value, str):
        return value + "x" if value else "x"
    if isinstance(value, list):
        if not value:
            return [0]
        if len(value) >= 2 and value[0] != value[-1]:
            return [value[-1], *value[1:-1], value[0]]
        return value[:-1]
    return None
