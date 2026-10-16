"""A problem's input rules: the schema, plus an optional validator for rules the schema
language can't express (the escape hatch in plan §5).

The validator is Python defining `validate(*args) -> str | None`: None if the input is
fine, otherwise a message for the learner. It always runs in the sandbox, whoever wrote it.
Random tests are generated from the schema and, if there's a validator, filtered through
it in one sandbox batch.
"""

import json
from dataclasses import dataclass
from typing import Any

from algolens.sandbox.client import SandboxClient, SandboxUnavailable
from algolens.schema.generate import SMALL, GenerationError, Profile, generate_many
from algolens.schema.model import Schema
from algolens.schema.validate import Issue, validate

MIN_ACCEPTANCE = 0.05  # below this the extra rules are too strict to sample from
BATCH = 250  # inputs per validator batch: small enough to finish even on a busy machine


@dataclass(frozen=True)
class InputRules:
    schema: Schema
    validator: str | None = None


def check_input(rules: InputRules, args: Any, client: SandboxClient) -> list[Issue]:
    """Issues with `args`; empty means it's a valid input for the problem."""
    issues = validate(rules.schema, args)
    if issues or not rules.validator:
        return issues
    verdict = _run_validator(rules.validator, [args], client)[0]
    return [] if verdict is None else [Issue("", verdict)]


def generate_tests(
    rules: InputRules, n: int, seed: int, client: SandboxClient | None, profile: Profile = SMALL
) -> list[list[Any]]:
    """`n` distinct valid inputs, deterministic for the seed. If fewer can be made, raises
    GenerationError with the ones that were made in `partial` (callers may test on those)."""
    out: list[list[Any]] = []
    seen: set[str] = set()
    problem = ""
    for round_ in range(6):
        wanted = n - len(out)
        if wanted <= 0:
            break
        try:
            candidates = generate_many(rules.schema, max(wanted * 3, 50),
                                       seed=seed * 1000 + round_, profile=profile)  # fmt: skip
        except GenerationError as exc:
            problem = str(exc)
            break
        fresh = []
        for c in candidates:
            key = json.dumps(c, sort_keys=True)
            if key not in seen:
                seen.add(key)
                fresh.append(c)
        if rules.validator:
            if client is None:
                raise ValueError("a validator needs the sandbox")
            verdicts = []
            for i in range(0, len(fresh), BATCH):
                verdicts += _run_validator(rules.validator, fresh[i : i + BATCH], client)
            accepted = [c for c, v in zip(fresh, verdicts, strict=True) if v is None]
            if fresh and len(accepted) / len(fresh) < MIN_ACCEPTANCE:
                problem = (f"only {len(accepted)} of {len(fresh)} generated inputs satisfy the "
                           "extra rules")  # fmt: skip
        else:
            accepted = fresh
        out += accepted[:wanted]
    if len(out) < n:
        why = f" ({problem})" if problem else ""
        raise GenerationError(
            f"could only generate {len(out)} distinct valid inputs of {n}{why}", partial=out
        )
    return out


def _run_validator(source: str, inputs: list[list[Any]], client: SandboxClient) -> list[str | None]:
    """The validator's verdict on each input. Anything that ran out of time (a busy machine
    can do that) is retried once on its own before its verdict counts."""
    results = _validator_batch(source, inputs, client, wall_s=240)
    retry = [i for i, r in enumerate(results) if r["outcome"] in ("timeout", "not_run")]
    if retry:
        again = _validator_batch(source, [inputs[i] for i in retry], client, wall_s=240)
        for i, r in zip(retry, again, strict=True):
            results[i] = r
    verdicts: list[str | None] = []
    for r in results:
        if r["outcome"] != "ok":
            verdicts.append(f"this input couldn't be checked ({r['outcome']}: {r['detail']})")
        elif r["value"] is None:
            verdicts.append(None)
        else:
            verdicts.append(str(r["value"]))
    return verdicts


def _validator_batch(source: str, inputs: list, client: SandboxClient, wall_s: int) -> list[dict]:
    resp = client.run_batch({
        "language": "python",
        "source": source,
        "entry": "validate",
        "tests": [{"id": str(i), "input": {"args": args}} for i, args in enumerate(inputs)],
        "per_test": {"cpu_ms": 1000, "wall_ms": 5000},
        "batch_wall_s": wall_s,
    })  # fmt: skip
    if resp["status"] not in ("ok", "batch_timeout"):
        raise SandboxUnavailable(
            f"input validator didn't run: {resp['status']} {resp.get('detail', '')}"
        )
    return list(resp["results"])  # on batch_timeout, unfinished inputs come back as not_run


def all_inputs(
    rules: InputRules, limit: int, client: SandboxClient | None
) -> list[list[Any]] | None:
    """Every valid input, when the schema has only integer and boolean parameters and at most
    `limit` combinations; otherwise None. Used when the input space is too small to draw
    `limit` distinct random inputs from: testing all of it is then the stronger check."""
    from algolens.schema.model import BoolT, IntT, resolve

    if not all(isinstance(p.type, IntT | BoolT) for p in rules.schema.params):
        return None
    combos: list[dict[str, Any]] = [{}]
    for p in rules.schema.params:
        nxt = []
        for env in combos:
            if isinstance(p.type, BoolT):
                values: list[Any] = [False, True]
            else:
                try:
                    lo, hi = resolve(p.type.min, env), resolve(p.type.max, env)
                except ValueError:
                    return None
                if hi - lo + 1 > limit:
                    return None
                values = list(range(lo, hi + 1))
            nxt += [{**env, p.name: v} for v in values]
            if len(nxt) > limit * 20:
                return None
        combos = nxt
    inputs = [[env[p.name] for p in rules.schema.params] for env in combos]
    valid = [args for args in inputs if not validate(rules.schema, args)]
    if rules.validator and valid:
        if client is None:
            return None
        verdicts = _run_validator(rules.validator, valid, client)
        valid = [a for a, v in zip(valid, verdicts, strict=True) if v is None]
    return valid if 0 < len(valid) <= limit else None
