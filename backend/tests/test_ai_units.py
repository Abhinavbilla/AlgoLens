"""Pieces of the AI pipeline that need neither a model nor the sandbox."""

import threading

import pytest
from pydantic import ValidationError

from algolens.ai.budget import Budget, BudgetExhausted
from algolens.ai.client import AIClient, AIUnavailable, extract_json, parse_role
from algolens.pipeline import prompts
from algolens.pipeline.models import ApproachList, ParsedProblem
from algolens.pipeline.solve import mutate
from algolens.verification.compare import same

# --- compare ---------------------------------------------------------------------------------


def test_exact_keeps_bool_and_int_apart():
    assert same("exact", [1, 2], [1, 2])
    assert not same("exact", True, 1)
    assert not same("exact", [True], [1])
    assert not same("exact", [1, 2], [2, 1])


def test_float_tolerance_is_absolute_or_relative():
    assert same("float", 0.1 + 0.2, 0.3)
    assert same("float", 1e12, 1e12 + 1)
    assert not same("float", 1.0, 1.001)
    assert not same("float", float("nan"), float("nan"))
    assert not same("float", True, 1.0)


def test_unordered_comparators():
    assert same("unordered", [[1, 2], [3]], [[3], [1, 2]])
    assert not same("unordered", [[1, 2], [3]], [[3], [2, 1]])
    assert same("unordered_nested", [[1, 2], [3]], [[3], [2, 1]])
    assert not same("unordered", [1, 1, 2], [1, 2, 2])
    assert not same("unordered", 1, [1])


def test_checker_kind_cannot_be_compared_directly():
    with pytest.raises(ValueError):
        same("checker", 1, 1)


# --- extract_json / roles ---------------------------------------------------------------------


def test_extract_json_tolerates_fences_and_chatter():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}
    assert extract_json('Sure! Here it is: {"a": "}"} hope that helps') == {"a": "}"}
    assert extract_json("[1, 2]") is None
    assert extract_json("not json") is None


def test_parse_role():
    assert parse_role("gemini:gemini-2.5-flash") == ("gemini", "gemini-2.5-flash")
    assert parse_role("groq:openai/gpt-oss-120b") == ("groq", "openai/gpt-oss-120b")
    for bad in ("gemini", "nope:model", "gemini:"):
        with pytest.raises(AIUnavailable):
            parse_role(bad)


def test_missing_key_is_unavailable_not_a_verdict(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = AIClient({"parse": "gemini:gemini-2.5-flash"})
    with pytest.raises(AIUnavailable):
        client.complete_json("parse", "s", "p", Budget(100_000))


# --- budget --------------------------------------------------------------------------------


def test_budget_reserves_worst_case_and_charges_actual():
    b = Budget(10_000)
    with b.reserve(6000, "parse") as charge:
        assert b.left == 4000
        with pytest.raises(BudgetExhausted), b.reserve(5000, "brute_a"):
            pass
        charge(1000)
    assert b.used == 1000 and b.left == 9000
    assert b.report()["by_stage"] == {"parse": 1000}


def test_failed_call_counts_its_whole_reservation():
    b = Budget(10_000)
    with pytest.raises(RuntimeError), b.reserve(3000, "parse"):
        raise RuntimeError("network")
    assert b.used == 3000


def test_parallel_reservations_cannot_overshoot():
    b = Budget(10_000)
    granted, refused = [], []
    gate = threading.Barrier(5)

    def worker():
        gate.wait()
        try:
            with b.reserve(3000, "x") as charge:
                granted.append(1)
                charge(3000)
        except BudgetExhausted:
            refused.append(1)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(granted) == 3 and len(refused) == 2 and b.used == 9000


def test_fake_client_charges_the_budget():
    client = AIClient({"parse": "fake:x"}, fake=lambda role, s, p: {"ok": True})
    b = Budget(100_000)
    reply = client.complete_json("parse", "system", "prompt", b)
    assert reply.data == {"ok": True} and 0 < b.used < 100


# --- models / prompts -------------------------------------------------------------------------


def test_parsed_problem_validation():
    p = ParsedProblem.model_validate({"in_scope": True, "function_name": "two_sum",
                                      "params": [{"name": "t", "type": {"kind": "binary_tree"}}]})  # fmt: skip
    assert p.comparator.kind == "exact" and p.convert() == ["binary_tree"]
    with pytest.raises(ValidationError):
        ParsedProblem.model_validate({"in_scope": True, "function_name": "not valid"})
    with pytest.raises(ValidationError):
        ParsedProblem.model_validate({"in_scope": True, "comparator": {"kind": "fuzzy"}})


def test_approach_list_must_have_one_or_two():
    one = {"name": "a", "key_idea": "b", "time": "O(n)", "space": "O(1)",
           "python_code": "def f(x):\n    return x", "cpp_code": "int main() { return 0; }"}  # fmt: skip
    assert len(ApproachList.model_validate({"approaches": [one]}).approaches) == 1
    for bad in ([], [one, one, one]):
        with pytest.raises(ValidationError):
            ApproachList.model_validate({"approaches": bad})


def test_brute_b_prompt_has_only_the_statement_and_signature():
    spec = {"function_name": "f", "params": [{"name": "nums"}, {"name": "k"}]}
    text = prompts.brute_b_prompt("STATEMENT", spec)
    assert "STATEMENT" in text and "def f(nums, k)" in text and "Parsed" not in text


def test_prompt_set_hash_is_stable():
    assert prompts.prompt_set_hash() == prompts.prompt_set_hash()
    assert len(prompts.prompt_set_hash()) == 16


def test_mutations_always_differ():
    for v in (True, 0, 1.5, "", "ab", [], [1], [1, 2], [[1], [2]], [3, 3]):
        assert mutate(v) != v
    assert mutate(None) is None


def test_json_mode_rejection_is_retried_without_json_mode(monkeypatch):
    from algolens.ai import client as cl

    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(cl, "MIN_INTERVAL", {**cl.MIN_INTERVAL, "groq": 0})
    bodies = []

    def fake_post(self, url, body, headers):
        bodies.append(dict(body))
        if "response_format" in body:
            raise cl.AIError('HTTP 400: {"error":{"code":"json_validate_failed"}}')
        return {"choices": [{"message": {"content": 'Here: {"ok": true}'}}], "usage": {}}

    monkeypatch.setattr(cl.AIClient, "_post", fake_post)
    reply = cl.AIClient({"parse": "groq:m"}).complete_json("parse", "s", "p", Budget(100_000))
    assert reply.data == {"ok": True} and len(bodies) == 2 and "response_format" not in bodies[1]


def test_visual_prompt_renders_literal_braces():
    assert (
        "Ellipsis" not in prompts.VISUAL_SYSTEM
        and "inside {...} in narration" in prompts.VISUAL_SYSTEM
    )
    assert "never wrapped in {}" in prompts.VISUAL_SYSTEM
    rules = prompts.CODE_RULES.format(fn="f", args="x")
    assert "int main()" in rules and "1-character STRINGS" in rules


def test_small_input_spaces_are_enumerated():
    from algolens.schema.model import compile_schema
    from algolens.schema.service import InputRules, all_inputs

    one = InputRules(
        compile_schema({"params": [{"name": "n", "type": {"kind": "int", "min": 1, "max": 45}}]})
    )
    assert all_inputs(one, 300, None) == [[n] for n in range(1, 46)]
    two = InputRules(compile_schema({"params": [
        {"name": "n", "type": {"kind": "int", "min": 1, "max": 5}},
        {"name": "k", "type": {"kind": "int", "min": 0, "max": "n"}}]}))  # fmt: skip
    assert len(all_inputs(two, 300, None)) == 2 + 3 + 4 + 5 + 6
    big = InputRules(
        compile_schema({"params": [{"name": "n", "type": {"kind": "int", "min": 1, "max": 1000}}]})
    )
    assert all_inputs(big, 300, None) is None
    arr = InputRules(
        compile_schema(
            {"params": [{"name": "a", "type": {"kind": "array", "of": {"kind": "int"}}}]}
        )
    )
    assert all_inputs(arr, 300, None) is None


def test_long_rate_limit_fails_fast_with_the_reason(monkeypatch):
    from algolens.ai import client as cl

    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(cl, "MIN_INTERVAL", {**cl.MIN_INTERVAL, "groq": 0})
    calls = []

    def fake_post(self, url, body, headers):
        calls.append(1)
        raise cl._Retryable(
            'HTTP 429: {"error":{"message":"Rate limit reached on tokens per day (TPD)"}}', 1128
        )

    monkeypatch.setattr(cl.AIClient, "_post", fake_post)
    with pytest.raises(cl.AIError, match="try again in about 19 min.*tokens per day"):
        cl.AIClient({"parse": "groq:m"}).complete_json("parse", "s", "p", Budget(100_000))
    assert calls == [1]


def test_request_too_large_retries_within_the_output_limit(monkeypatch):
    from algolens.ai import client as cl

    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(cl, "MIN_INTERVAL", {**cl.MIN_INTERVAL, "groq": 0})
    sizes = []

    def fake_post(self, url, body, headers):
        sizes.append(body["max_tokens"])
        if body["max_tokens"] > 2000:
            raise cl._Retryable("HTTP 429: Request too large ... output tokens per minute (OTPM): "
                                "Limit 2000, Requested 6436", 0)  # fmt: skip
        return {"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}}

    monkeypatch.setattr(cl.AIClient, "_post", fake_post)
    reply = cl.AIClient({"brute_b": "groq:q"}).complete_json("brute_b", "s", "p", Budget(100_000))
    assert reply.data == {"ok": True} and sizes == [8000, 1984]


def test_request_over_the_per_minute_limit_shrinks_max_tokens(monkeypatch):
    from algolens.ai import client as cl

    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(cl, "MIN_INTERVAL", {**cl.MIN_INTERVAL, "groq": 0})
    sizes = []

    def fake_post(self, url, body, headers):
        sizes.append(body["max_tokens"])
        if body["max_tokens"] == 8000:
            raise cl.AIError('HTTP 413: {"error":{"message":"Request too large for model `m` on tokens '
                             'per minute (TPM): Limit 8000, Requested 8166, please reduce"}}')  # fmt: skip
        return {"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}}

    monkeypatch.setattr(cl.AIClient, "_post", fake_post)
    reply = cl.AIClient({"parse": "groq:m"}).complete_json("parse", "s", "p", Budget(100_000))
    assert reply.data == {"ok": True} and sizes == [8000, 7770]
