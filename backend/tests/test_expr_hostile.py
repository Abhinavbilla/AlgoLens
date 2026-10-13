"""Hostile templates (plan §7.5, M1 security suite).

Narration runs outside the sandbox, so every one of these must be rejected or evaluate to
a clean ExprError ("no match"): no other exception, no side effect, and no slowdown.
"""

import contextlib
import random
import string
import time

import pytest

from algolens.narration.expr import Env, ExprError, evaluate, parse
from algolens.narration.template import parse_template

STATE = {"nums": [1, 2, 3], "x": 5, "s": "abc", "node": {"val": 1, "next": None}}
ENV = Env(now=STATE.__getitem__, before=STATE.__getitem__)

HOSTILE_EXPRESSIONS = [
    # reaching Python internals
    "__import__('os')",
    "__import__('os').system('id')",
    "().__class__.__mro__",
    "x.__class__",
    "x.__dict__",
    "nums.__len__",
    "s.upper",
    "node.__class__",
    "__builtins__",
    "_x__y",
    # calls, lambdas, comprehensions, other syntax
    "open('/etc/passwd')",
    "eval('1')",
    "exec('1')",
    "getattr(x, 'real')",
    "len.__self__",
    "lambda: 1",
    "(lambda: 1)()",
    "[i for i in nums]",
    "{k: 1 for k in nums}",
    "[1, 2, 3]",
    "{'a': 1}",
    "nums[0:2]",
    "nums[::-1]",
    "x if x else 0",
    "x := 3",
    "x = 3",
    "x; x",
    "x ** 2",
    "x @ x",
    "x | 1",
    "x & 1",
    "x ^ 1",
    "~x",
    "x << 2",
    "+x",
    "f'{x}'",
    "b'abc'",
    "r'abc'",
    "'\\x41'",
    "'\\u0041'",
    "x\\\n+1",
    "x in nums",
    "x is None",
    "*nums",
    "...",
    "old(old(x))",
    "old(x + 1)",
    "old(len(nums))",
    "len()",
    "len(x, x)",
    "len",
    "old",
    # resource exhaustion
    '"a" * 10**9',
    '"a" * 1000000000',
    "s * 100000000",
    "nums * 100000000",
    "9" * 400,
    "99999999999999999999",
    "(" * 10_000 + "x" + ")" * 10_000,
    "-" * 150 + "x",
    "not " * 40 + "x",
    "x[" * 40 + "0" + "]" * 40,
    "999999999999999999 * 999999999999999999",
    # unicode lookalikes and control characters
    "nums[а]",  # Cyrillic a
    "х",  # Cyrillic x
    "x​",  # zero-width space
    "x\x00",
    "x\n",
    "ｘ",  # fullwidth x
    "",
    "   ",
]

HOSTILE_TEMPLATES = [
    "{nums.__class__}",
    "{x.__class__.__mro__}",
    "{__import__('os')}",
    "{x!r}",
    "{x:>{1000000000}}",
    "{x:{x}}",
    "{0}",
    "{",
    "}",
    "{x",
    "x}",
    "{{x}",
    "{x}}",
    "{x{y}}",
    "{'}'}",
    '{"{"}',
    "{x} " * 11,
    "a" * 501,
    "{" * 10_000,
]


def _assert_contained(fn) -> None:
    start = time.perf_counter()
    with contextlib.suppress(ExprError):
        fn()
    assert time.perf_counter() - start < 0.05, "took too long"


@pytest.mark.parametrize("src", HOSTILE_EXPRESSIONS)
def test_hostile_expressions_are_fast_to_reject(src):
    _assert_contained(lambda: evaluate(parse(src), ENV))


@pytest.mark.parametrize("src", HOSTILE_EXPRESSIONS)
def test_hostile_expressions_are_rejected(src):
    with pytest.raises(ExprError):
        evaluate(parse(src), ENV)


@pytest.mark.parametrize("text", HOSTILE_TEMPLATES)
def test_hostile_templates_are_rejected(text):
    _assert_contained(lambda: parse_template(text))
    if text not in ("{x} " * 11,):
        with pytest.raises(ExprError):
            parse_template(text)


# Look like str.format tricks but are legal in our language, and harmless: indexing over
# snapshot data, and escaped braces around a placeholder.
TRICKY_BUT_LEGAL = ["{x[0]}", "{{{x}}}", "{nums[0]}"]


@pytest.mark.parametrize("text", TRICKY_BUT_LEGAL)
def test_tricky_but_legal_templates_parse_and_stay_contained(text):
    _assert_contained(lambda: parse_template(text))
    parse_template(text)


def test_too_many_placeholders_rejected():
    with pytest.raises(ExprError):
        parse_template("{x} " * 11)


def test_no_python_object_is_ever_returned():
    # Whatever evaluates must be plain JSON data.
    for src in ["nums", "node", "s", "x", "len(nums)", "old(nums)", "node.next"]:
        value = evaluate(parse(src), ENV)
        assert isinstance(value, int | float | str | bool | list | dict | type(None))


def _fuzz_inputs(rng: random.Random, n: int):
    tokens = ["x", "nums", "s", "node", "[", "]", "(", ")", ".", "val", "next", "+", "-", "*",
              "//", "%", "==", "<", "and", "or", "not", "len", "old", "0", "1", "-1",
              "999999999999999999", "'a'", '"b"', "__class__", "True", "None", " ", "{", "}",
              "**", ",", ":", "lambda", "\\"]  # fmt: skip
    for _ in range(n):
        if rng.random() < 0.5:
            yield "".join(rng.choice(tokens) for _ in range(rng.randint(1, 30)))
        else:
            alphabet = string.printable + "а​ｘ"
            yield "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))


def test_fuzz_only_ever_raises_expr_error():
    rng = random.Random(1234)
    for src in _fuzz_inputs(rng, 5000):
        try:
            value = evaluate(parse(src), ENV)
        except ExprError:
            continue
        assert isinstance(value, int | float | str | bool | list | dict | type(None)), src
        assert not (isinstance(value, int) and abs(value) > 10**18), src


def test_fuzz_templates_only_ever_raise_expr_error():
    rng = random.Random(99)
    for src in _fuzz_inputs(rng, 3000):
        with contextlib.suppress(ExprError):
            parse_template(src)
