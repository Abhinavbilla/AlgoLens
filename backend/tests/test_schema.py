import json
import random

import pytest

from algolens.schema.generate import GenerationError, Profile, generate, generate_many
from algolens.schema.model import SchemaError, compile_schema
from algolens.schema.validate import validate

SCHEMAS = {
    "ints": {"params": [{"name": "a", "type": {"kind": "int", "min": -5, "max": 5}},
                        {"name": "b", "type": {"kind": "int", "min": "a", "max": "a + 10"}}]},
    "sorted-array": {"params": [{"name": "nums", "type": {"kind": "array", "of": {"kind": "int"},
                                                          "len": {"min": 0, "max": 100}, "sorted": True}},
                                {"name": "target", "type": {"kind": "int"}}]},
    "distinct-desc": {"params": [{"name": "xs", "type": {"kind": "array", "of": {"kind": "int", "min": 0, "max": 9},
                                                         "len": {"min": 1, "max": 6}, "distinct": True,
                                                         "sorted": "desc"}}]},
    "permutation": {"params": [{"name": "p", "type": {"kind": "array", "of": {"kind": "int"},
                                                      "len": {"min": 1, "max": 9}, "permutation": {"start": 1}}}]},
    "k-in-range": {"params": [{"name": "nums", "type": {"kind": "array", "of": {"kind": "int"},
                                                        "len": {"min": 1, "max": 50}}},
                              {"name": "k", "type": {"kind": "int", "min": 1, "max": "len(nums)"}}],
                   "constraints": [{"check": "k <= len(nums)"}]},
    "strings": {"params": [{"name": "s", "type": {"kind": "string", "len": {"min": 0, "max": 30}}},
                           {"name": "p", "type": {"kind": "string", "chars": "parens", "len": {"min": 0, "max": 12},
                                                  "valid_parentheses": True}}]},
    "matrix": {"params": [{"name": "m", "type": {"kind": "matrix", "of": {"kind": "int", "min": 0, "max": 9},
                                                 "rows": {"min": 1, "max": 6}, "cols": {"min": 1, "max": 6}}}]},
    "grid": {"params": [{"name": "g", "type": {"kind": "grid", "chars": "01", "rows": {"min": 1, "max": 8},
                                               "cols": {"min": 1, "max": 8}}}]},
    "list-and-tree": {"params": [{"name": "head", "type": {"kind": "linked_list", "of": {"kind": "int"},
                                                           "len": {"min": 0, "max": 10}}},
                                 {"name": "root", "type": {"kind": "binary_tree", "of": {"kind": "int"},
                                                           "nodes": {"min": 0, "max": 20}}}]},
    "bst": {"params": [{"name": "root", "type": {"kind": "binary_tree", "of": {"kind": "int", "min": -100, "max": 100},
                                                 "nodes": {"min": 1, "max": 15}, "bst": True}}]},
    "weighted-connected": {"params": [
        {"name": "n", "type": {"kind": "int", "min": 1, "max": 8}},
        {"name": "edges", "type": {"kind": "edges", "nodes": "n", "count": {"min": 0, "max": 20},
                                   "weighted": True, "weight": {"min": 1, "max": 9}, "connected": True}}]},
    "dag": {"params": [{"name": "n", "type": {"kind": "int", "min": 0, "max": 8}},
                       {"name": "edges", "type": {"kind": "edges", "nodes": "n", "count": {"min": 0, "max": 15},
                                                  "directed": True, "dag": True}}]},
    "tree-edges": {"params": [{"name": "n", "type": {"kind": "int", "min": 1, "max": 9}},
                              {"name": "edges", "type": {"kind": "edges", "nodes": "n", "tree": True,
                                                         "count": {"min": 0, "max": "n"}}}]},
    "ops": {"params": [{"name": "nums", "type": {"kind": "array", "of": {"kind": "int", "min": 0, "max": 9},
                                                 "len": {"min": 1, "max": 6}}},
                       {"name": "queries", "type": {"kind": "ops", "len": {"min": 1, "max": 6}, "ops": [
                           {"name": "update", "args": [{"kind": "int", "min": 0, "max": "len(nums) - 1"},
                                                       {"kind": "int", "min": 0, "max": 9}]},
                           {"name": "sum", "args": [{"kind": "int", "min": 0, "max": "len(nums) - 1"}]}]}}]},
}  # fmt: skip


@pytest.mark.parametrize("name", SCHEMAS)
def test_generated_inputs_always_validate(name):
    schema = compile_schema(SCHEMAS[name])
    for args in generate_many(schema, 400, seed=7):
        assert validate(schema, args) == [], (name, args)


@pytest.mark.parametrize("name", SCHEMAS)
def test_generation_is_deterministic(name):
    schema = compile_schema(SCHEMAS[name])
    assert generate_many(schema, 30, seed=3) == generate_many(schema, 30, seed=3)


def test_small_profile_covers_edge_cases():
    schema = compile_schema(SCHEMAS["sorted-array"])
    inputs = generate_many(schema, 300, seed=1)
    lengths = {len(a[0]) for a in inputs}
    assert 0 in lengths and max(lengths) <= 8  # empty arrays appear; brute-force friendly
    assert any(len(a[0]) > 1 and len(set(a[0])) == 1 for a in inputs)  # all equal
    assert any(len(set(a[0])) < len(a[0]) for a in inputs)  # duplicates
    values = [x for a in inputs for x in a[0]]
    assert -(10**9) in values or 10**9 in values  # range extremes
    assert sum(abs(x) <= 20 for x in values) > 0.7 * len(values)  # but mostly small


def test_size_profile_sets_collection_sizes():
    schema = compile_schema(SCHEMAS["sorted-array"])
    args = generate(schema, random.Random(0), Profile(size=60))
    assert len(args[0]) == 60
    assert validate(schema, args) == []
    clamped = generate(schema, random.Random(0), Profile(size=5000))
    assert len(clamped[0]) == 100  # never beyond the declared maximum


def test_graph_generators_respect_their_properties():
    for name in ("weighted-connected", "dag", "tree-edges"):
        schema = compile_schema(SCHEMAS[name])
        for args in generate_many(schema, 200, seed=11):
            assert validate(schema, args) == [], (name, args)
    tree = compile_schema(SCHEMAS["tree-edges"])
    for n, edges in generate_many(tree, 50, seed=2):
        assert len(edges) == n - 1


def test_contradictory_schema_fails_loudly():
    schema = compile_schema({"params": [
        {"name": "xs", "type": {"kind": "array", "of": {"kind": "int", "min": 0, "max": 2},
                                "len": {"min": 5, "max": 5}, "distinct": True}}]})  # fmt: skip
    with pytest.raises(GenerationError):
        generate(schema, random.Random(0))


# --- validation messages ----------------------------------------------------------------------


def issues(name, args):
    return [str(i) for i in validate(compile_schema(SCHEMAS[name]), args)]


@pytest.mark.parametrize(
    ("name", "args", "expected"),
    [
        ("ints", [9, 0], "a: must be at most 5 (got 9)"),
        ("ints", [1, 50], "b: must be at most 11 (got 50)"),
        ("ints", [True, 0], "a: must be a whole number (got true)"),
        ("ints", [1], "expected 2 arguments (a, b), got 1"),
        ("sorted-array", [[1, 5, 2], 3], "nums: must be sorted in ascending order (nums[2] = 2 comes after 5)"),
        ("sorted-array", [[1, "x"], 3], "nums[1]: must be a whole number (got 'x')"),
        ("sorted-array", [list(range(101)), 3], "nums: must have at most 100 values (got 101)"),
        ("distinct-desc", [[5, 5]], "xs[1]: repeats 5 (already at xs[0]); values must be distinct"),
        ("permutation", [[1, 3]], "p: must contain each of 1..2 exactly once"),
        ("k-in-range", [[1, 2], 3], "k: must be at most 2 (got 3)"),
        ("strings", ["abC", ""], "s: may only contain lowercase letters (found 'C')"),
        ("strings", ["ab", "(()"], "p: must be a balanced string of parentheses"),
        ("matrix", [[[1, 2], [3]]], "m[1]: every row must have 2 values (this one has 1)"),
        ("grid", [[["0", "2"]]], "g[0][1]: must be one of '0' '1' (got '2')"),
        ("list-and-tree", [[], [None, 1]], "root[0]: the root can't be null; use [] for an empty tree"),
        ("list-and-tree", [[], [1, None, None, 2]], "root[3]: has no parent; there are more values than open child slots"),
        ("bst", [[5, 7, 3]], "root: isn't a binary search tree: 5 comes after 7 in order"),
        ("weighted-connected", [3, [[0, 1, 5]]], "edges: the graph must be connected"),
        ("weighted-connected", [3, [[0, 3, 5]]], "edges[0][1]: must be a node number from 0 to 2 (got 3)"),
        ("weighted-connected", [2, [[0, 1]]], "edges[0]: each edge must be [u, v, weight]"),
        ("dag", [3, [[0, 1], [1, 2], [2, 0]]], "edges: must not contain a cycle"),
        ("dag", [2, [[0, 0]]], "edges[0]: connects node 0 to itself; self-loops aren't allowed"),
        ("tree-edges", [3, [[0, 1], [1, 2], [0, 2]]], "edges: a tree on 3 nodes has exactly 2 edges (got 3)"),
        ("ops", [[1, 2], [["update", 5, 1]]], "queries[0][1]: must be at most 1 (got 5)"),
        ("ops", [[1, 2], [["delete", 0]]], "queries[0]: must start with one of update, sum"),
    ],
)  # fmt: skip
def test_validation_messages(name, args, expected):
    assert expected in issues(name, args)


def test_valid_inputs_have_no_issues():
    assert issues("sorted-array", [[1, 3, 3, 5], 4]) == []
    assert issues("bst", [[5, 3, 8, None, 4]]) == []
    assert issues("tree-edges", [3, [[0, 1], [2, 1]]]) == []


def test_constraint_message_is_used():
    schema = compile_schema({"params": [{"name": "a", "type": {"kind": "int"}},
                                        {"name": "b", "type": {"kind": "int"}}],
                             "constraints": [{"check": "a < b", "message": "a must be smaller than b"}]})  # fmt: skip
    assert [str(i) for i in validate(schema, [3, 1])] == ["a must be smaller than b"]


# --- compiling ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"params": []},
        {"params": [{"name": "1x", "type": {"kind": "int"}}]},
        {"params": [{"name": "a", "type": {"kind": "int"}}, {"name": "a", "type": {"kind": "int"}}]},
        {"params": [{"name": "a", "type": {"kind": "nope"}}]},
        {"params": [{"name": "a", "type": {"kind": "int", "max": "b"}}, {"name": "b", "type": {"kind": "int"}}]},
        {"params": [{"name": "a", "type": {"kind": "int", "max": "__import__('os')"}}]},
        {"params": [{"name": "a", "type": {"kind": "array", "of": {"kind": "int"}, "sorted": "sideways"}}]},
        {"params": [{"name": "a", "type": {"kind": "array", "of": {"kind": "int"}, "len": {"min": 5, "max": 2}}}]},
        {"params": [{"name": "e", "type": {"kind": "edges", "nodes": 3, "dag": True}}]},
        {"params": [{"name": "a", "type": {"kind": "int"}}], "constraints": [{"check": "zz > 1"}]},
    ],
)  # fmt: skip
def test_malformed_schemas_are_rejected(raw):
    with pytest.raises(SchemaError):
        compile_schema(raw)


def test_generation_that_falls_short_hands_back_what_it_made():
    from algolens.schema.service import InputRules, generate_tests

    schema = compile_schema(
        {
            "params": [
                {
                    "name": "nums",
                    "type": {
                        "kind": "array",
                        "of": {"kind": "int", "min": 0, "max": 2},
                        "len": {"min": 1, "max": 2},
                    },
                }
            ]
        }
    )
    with pytest.raises(GenerationError) as info:
        generate_tests(InputRules(schema), 300, seed=1, client=None)
    partial = info.value.partial
    assert 0 < len(partial) <= 12  # 3 + 9 distinct inputs exist
    assert len({json.dumps(p) for p in partial}) == len(partial)
