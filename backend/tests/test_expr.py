import pytest

from algolens.narration.expr import Env, EvalError, ParseError, evaluate, parse
from algolens.narration.template import parse_condition, parse_template

STATE = {
    "nums": [2, 7, 11, 15],
    "l": 0,
    "r": 3,
    "target": 9,
    "seen": {"2": 0, "7": 1},
    "word": "abc",
    "node": {"val": 5, "next": None, "left": None, "right": None},
    "flag": True,
    "half": 2.5,
}
BEFORE = {**STATE, "r": 4, "nums": [2, 7, 11, 15, 20]}


def ev(src, state=STATE, before=BEFORE):
    env = Env(now=state.__getitem__, before=before.__getitem__ if before else None)
    return evaluate(parse(src), env)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("nums[l] + nums[r]", 17),
        ("nums[l] + nums[r] > target", True),
        ("2 + 3 * 4", 14),
        ("(2 + 3) * 4", 20),
        ("-2 * 3", -6),
        ("7 // 2", 3),
        ("-7 // 2", -4),
        ("7 % 3", 1),
        ("half * 2", 5.0),
        ("nums[-1]", 15),
        ("nums[r - 1]", 11),
        ("seen[2]", 0),
        ("seen['7']", 1),
        ("node.val", 5),
        ("node.next == None", True),
        ("len(nums)", 4),
        ("len(word)", 3),
        ("word[1] == 'b'", True),
        ("l < r < len(nums)", True),
        ("l < r < 2", False),
        ("not flag", False),
        ("flag and r > l", True),
        ("r == 0 or l == 0", True),
        ("not l == r", True),
        ("old(r)", 4),
        ("old(r) - r", 1),
        ("old(nums[r])", 20),
        ("len(old(nums))", 5),
        ('"quote\\"d"', 'quote"d'),
    ],
)
def test_evaluates_like_python(src, expected):
    assert ev(src) == expected


@pytest.mark.parametrize(
    "src",
    [
        "missing",
        "nums[10]",
        "nums['a']",
        "nums[True]",
        "seen[99]",
        "word + 'x'",
        "nums + 1",
        "flag + 1",
        "r // 0",
        "r % 0",
        "node.val.val",
        "nums.val",
        "'a' < 1",
        "len(r)",
        "999999999999999999 * 2",
        "-(999999999999999999 * 2)",
    ],
)
def test_bad_evaluations_raise_eval_error(src):
    with pytest.raises(EvalError):
        ev(src)


def test_old_without_before_state_is_an_eval_error():
    with pytest.raises(EvalError):
        ev("old(r)", before=None)


def test_condition_uses_full_language():
    node = parse_condition("nums[l] + nums[r] > target and not flag == False")
    assert evaluate(node, Env(now=STATE.__getitem__)) is True


@pytest.mark.parametrize(
    ("text", "placeholders", "computed"),
    [
        ("{r} moves left", ["r"], [False]),
        ("{nums[l]} plus {nums[r]} is more than {target}", ["nums[l]", "nums[r]", "target"],
         [False, False, False]),
        ("the sum is {nums[l] + nums[r]}", ["nums[l] + nums[r]"], [True]),
        ("stack has {len(stack)} items", ["len(stack)"], [True]),
        ("from {old(r)} to {r}", ["old(r)", "r"], [False, False]),
        ("first is {nums[0]}", ["nums[0]"], [False]),
        ("next is {nums[i + 1]}", ["nums[i + 1]"], [False]),
        ("{{literal braces}} and {x}", ["x"], [False]),
        ("no placeholders at all", [], []),
    ],
)  # fmt: skip
def test_templates_parse(text, placeholders, computed):
    t = parse_template(text)
    assert [p.source for p in t.placeholders] == placeholders
    assert [p.computed for p in t.placeholders] == computed


def test_literal_braces_stay_in_text():
    t = parse_template("{{a}} {x}")
    assert t.segments[0] == "{a} "


@pytest.mark.parametrize(
    "text",
    [
        "{r > l} is shown",  # comparison in text
        "{flag and x}",
        "{not x}",
        "{nums[i] + 3}",  # only -2..2 may be operands
        "{j * 10}",
        "{j - -3}",
        "{2 + 2}",  # no value from the state at all
        "{1 - 2}",
        "{'hello'}",
        "{True}",
        "{len(nums[0] + 1)}",
        "{}",
        "{ }",
    ],
)
def test_templates_reject_ungrounded_or_logical_text(text):
    with pytest.raises(ParseError):
        parse_template(text)


@pytest.mark.parametrize("text", ["{j + 1}", "{j - 2}", "{nums[i] + -1}", "{2 * k}", "{-1 + r}"])
def test_small_constants_are_allowed_as_operands(text):
    (p,) = parse_template(text).placeholders
    assert p.computed
