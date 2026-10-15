"""Prompts for each AI role. Every reply must be one JSON object (see pipeline/models.py).

Brute B is deliberately given only the raw statement and the function signature, never the
parsed spec or anyone else's code (plan §6.2), so a misreading elsewhere shows up as a
disagreement instead of being copied.
"""

import hashlib
import json

from algolens.animation import panels as _panels
from algolens.narration import template as _template

SCHEMA_GUIDE = """\
Input schema language (each param: {"name": ..., "type": {...}}):
  {"kind":"int","min":M,"max":N}           {"kind":"float","min":M,"max":N}    {"kind":"bool"}
  {"kind":"string","len":{"min":0,"max":N},"chars":"lowercase|uppercase|letters|digits|alnum|binary|parens|<exact chars>","valid_parentheses":false}
  {"kind":"array","of":<type>,"len":{"min":0,"max":N},"sorted":false|"asc"|"desc","distinct":false,"permutation":{"start":0|1}}
  {"kind":"matrix","of":<type>,"rows":{"min":1,"max":N},"cols":{"min":1,"max":N}}
  {"kind":"grid","chars":".#","rows":{...},"cols":{...}}          (list of lists of 1-char strings)
  {"kind":"linked_list","of":<type>,"len":{...}}                   (given as a plain list)
  {"kind":"binary_tree","of":<type>,"nodes":{"min":0,"max":N},"bst":false} (level order, null for gaps)
  {"kind":"edges","nodes":"n","count":{"min":0,"max":N},"directed":false,"weighted":false,
   "weight":{"min":1,"max":100},"connected":false,"dag":false,"tree":false}   (list of [u,v] or [u,v,w], nodes 0..n-1)
  {"kind":"ops","len":{...},"ops":[{"name":"update","args":[<type>,...]},...]} (list of [name, *args])
Bounds may be integers or expressions over EARLIER params, e.g. "len(nums)", "n - 1".
constraints: [{"check": "k <= len(nums)", "message": "k can't exceed the length of nums"}]
Use the problem's real limits. Every example's args must satisfy the schema.
"""

CODE_RULES = """\
Code rules (the code is run and checked automatically):
- Python: define `def {fn}({args}):` at top level, returning a JSON-serializable value.
  Binary-tree arguments arrive as TreeNode(val, left, right) and linked lists as ListNode(val, next);
  both classes already exist: don't define or import them. Return a TreeNode/ListNode if the problem
  returns a tree/list. Only these imports are allowed: collections, heapq, math, bisect,
  itertools, functools, typing, operator, string, dataclasses. No randomness, no I/O, no sys.
  Write plain, readable code: it will be animated step by step for learners.
- C++17: a complete program WITH an `int main()` (the program is compiled and run on its own).
  Start with `#include <algolens.h>`: it brings in the common standard headers and provides
  nlohmann::json as algolens::Json, read_input() and emit(). Read the input JSON, whose "args" array holds the
  arguments in order. Trees and linked lists: use the provided algolens::TreeNode
  (val, left, right) / algolens::ListNode (val, next) with algolens::build_tree(in["args"][0]),
  algolens::build_list(...), and return algolens::to_json(root_or_head). Don't write your own. Print nothing else that matters; emit the result as JSON:
      int main() {{
          auto in = algolens::Json::parse(algolens::read_input());
          auto nums = in["args"][0].get<std::vector<long long>>();
          algolens::emit(algolens::Json({fn}(nums)).dump());
      }}
  Return trees as level-order lists (trailing nulls dropped). Use long long for integers.
  Always convert JSON with .get<T>() before use (e.g. in["args"][1].get<long long>(),
  .get<std::string>(), .get<std::vector<std::vector<long long>>>()); never pass a Json value
  where a C++ type is expected. Convert your result to algolens::Json before .dump().
  Grids of characters arrive as lists of 1-character STRINGS: read them with
  .get<std::vector<std::vector<std::string>>>() and compare with "1" (a std::string), never as
  char. Strings: .get<std::string>(). Booleans: .get<bool>(); emit true/false, not 1/0.
- The Python and C++ versions must be the same algorithm, with the same output for every input.
"""


def _sig(spec: dict) -> tuple[str, str]:
    return spec["function_name"], ", ".join(p["name"] for p in spec["params"])


PARSE_SYSTEM = f"""\
You read a data-structures-and-algorithms problem statement and describe it precisely as JSON.
Reply with ONE JSON object:
{{"in_scope": bool, "rejection_reason": str, "title": str, "function_name": str,
  "params": [...], "constraints": [...], "output": str,
  "result_kind": null | "binary_tree" | "linked_list",
  "comparator": {{"kind": "exact"|"float"|"unordered"|"unordered_nested"|"checker", "tolerance": 1e-6}},
  "examples": [{{"args": [...], "expected": ...}}], "patterns": [str],
  "extra_rules_python": str}}
In scope: arrays, strings, hashing, two pointers, sliding window, prefix sums, stacks, queues,
monotonic stacks, heaps, linked lists, binary trees, graphs (BFS, DFS, shortest paths,
topological sort, union-find), grids, recursion and backtracking, 1D/2D dynamic programming,
segment trees. Out of scope (set in_scope false and explain in one sentence): not a DSA problem,
mostly maths/proofs/geometry, interactive problems, random answers, class-design problems
("implement a class"), or a statement too ambiguous or contradictory to pin down (say what's unclear).
comparator: "exact" unless several answers are valid. "float" for real-number answers.
"unordered" when a list may come back in any order; "unordered_nested" when inner lists may too.
"checker" only when many different answers are valid (e.g. "return any valid path").
examples: the statement's worked examples, as given (args in parameter order, expected output).
extra_rules_python: "" unless an input rule can't be written in the schema; then Python source
defining validate(<params>) returning None if the input is fine, else a short message.
{SCHEMA_GUIDE}"""


def parse_prompt(statement: str, previous_problem: str = "") -> str:
    text = f"Problem statement:\n<<<\n{statement}\n>>>\n"
    if previous_problem:
        text += f"\nYour previous answer had this problem; fix it:\n{previous_problem}\n"
    return text


def _spec_text(spec: dict) -> str:
    keep = {
        k: spec[k]
        for k in (
            "title",
            "function_name",
            "params",
            "constraints",
            "output",
            "result_kind",
            "comparator",
            "examples",
        )
    }
    return json.dumps(keep, indent=1)


BRUTE_A_SYSTEM = """\
You write the simplest possible CORRECT solution to an algorithms problem: a brute force that
directly simulates or enumerates exactly what the statement asks, with no cleverness. It only
needs to be fast enough for small inputs. Correctness is everything: it is the reference other
solutions are checked against.
Reply with ONE JSON object: {"name": "Brute force", "key_idea": str, "time": str (just the big-O,
e.g. "O(n^2)"), "space": str,
"python_code": str, "cpp_code": str}"""


def brute_a_prompt(statement: str, spec: dict) -> str:
    fn, args = _sig(spec)
    return (
        f"Problem statement:\n<<<\n{statement}\n>>>\n\nParsed description:\n{_spec_text(spec)}\n\n"
        + CODE_RULES.format(fn=fn, args=args)
    )


BRUTE_B_SYSTEM = """\
You are an independent checker. First restate the problem in your own words and work through
each worked example by hand. Then write the most obviously correct exhaustive solution you can:
try every candidate (recursion or full enumeration), with no optimisation at all. It only has to
handle tiny inputs.
Reply with ONE JSON object: {"restatement": str, "python_code": str}"""


def brute_b_prompt(statement: str, spec: dict, failed_example: str = "") -> str:
    fn, args = _sig(spec)
    text = (
        f"Problem statement:\n<<<\n{statement}\n>>>\n\n"
        f"Write Python only: `def {fn}({args}):`. Binary-tree arguments arrive as "
        "TreeNode(val, left, right), linked lists as ListNode(val, next) (both already "
        "defined). Allowed imports: collections, heapq, math, bisect, itertools, functools, "
        "typing, operator, string, dataclasses."
    )
    if failed_example:
        text += f"\n\nA previous attempt got this worked example wrong:\n{failed_example}\n"
    return text


APPROACHES_SYSTEM = """\
You write efficient solutions to an algorithms problem, for learners. Give one or two approaches
that improve on brute force, ordered from simpler to more efficient; the last should be optimal.
A brute force is written separately: do NOT include one. Every approach you give must have a
strictly better time complexity than trying all candidates (e.g. O(n) or O(n log n) instead of
O(n^2)). If only one improvement exists, give just one.
Reply with ONE JSON object: {"approaches": [{"name": str, "key_idea": str (one line),
"time": str (just the big-O, e.g. "O(n log n)"), "space": str (e.g. "O(1)"), "python_code": str, "cpp_code": str}, ...]}"""


def approaches_prompt(statement: str, spec: dict) -> str:
    fn, args = _sig(spec)
    return (
        f"Problem statement:\n<<<\n{statement}\n>>>\n\nParsed description:\n{_spec_text(spec)}\n\n"
        + CODE_RULES.format(fn=fn, args=args)
    )


REPAIR_SYSTEM = """\
A solution to an algorithms problem gives a wrong result on a specific input. Find the bug and
return the corrected solution, keeping the same approach.
Reply with ONE JSON object: {"name": str, "key_idea": str, "time": str, "space": str,
"python_code": str, "cpp_code": str}"""


def repair_prompt(statement: str, spec: dict, approach: dict, failure: str) -> str:
    fn, args = _sig(spec)
    return (
        f"Problem statement:\n<<<\n{statement}\n>>>\n\nParsed description:\n{_spec_text(spec)}\n\n"
        f"Current solution ({approach['name']}):\nPython:\n{approach['python_code']}\n\n"
        f"C++:\n{approach['cpp_code']}\n\nWhat went wrong:\n{failure}\n\n"
        + CODE_RULES.format(fn=fn, args=args)
    )


CHECKER_SYSTEM = """\
Several different outputs are correct for this problem. Write a Python checker that decides
whether one output is a correct answer for one input. Be strict: accept every correct answer and
reject anything that isn't one.
Reply with ONE JSON object: {"python_code": str} defining
`def check(<the input params, in order>, output) -> bool`."""


def checker_prompt(statement: str, spec: dict) -> str:
    return f"Problem statement:\n<<<\n{statement}\n>>>\n\nParsed description:\n{_spec_text(spec)}\n"


VISUAL_SYSTEM = f"""\
You design a step-by-step animation of a Python solution for learners. The code is run with a
tracer; after each line runs, a frame records every variable. You choose what to draw (panels)
and write one-sentence narration templates per line. You never write values yourself: every
value shown comes from the recorded state through expressions.
Reply with ONE JSON object:
{{"visual": {{"panels": [...]}}, "narration": [{{"line": int, "next": int|"return" (optional),
  "when": str (optional condition), "text": str}}, ...], "cpp_lines": {{"<python line>": <C++ line>}}}}

PANELS (draw the main data structure first, then a "vars" panel with the key scalars).
For tree and linked_list panels, `var` and pointer `at` must be plain variable names (e.g.
"root", "node"), not expressions.
Panel fields are bare expressions, e.g. "var": "nums", "at": "i + 1" - never wrapped in {{}}.
Only narration `text` uses {{...}} placeholders.
{_panels.__doc__}
NARRATION. A template applies to a frame when `line` is the line that just ran, `next` (if
given) is the line that runs next (use it to say which branch was taken), and `when` (if given)
is true. The first applicable template wins, so templates for the same line must not overlap
unless they say the same thing. Lines with no template get a neutral sentence automatically.
Write for a learner: say WHY, not just what ("{{s}} < {{target}}: too small, so move l right").
{_template.__doc__}
NOT allowed inside {{...}} in narration text (these make a template invalid and it is dropped):
`in` / `not in`, any call except len() and old() (no max(), min(), sum(), str(), methods),
slicing, comparisons or and/or/not (put conditions in "when"), and string literals.
Never write a number directly in the sentence ("to 0", "index 1"): every number must come from a
{{...}} placeholder, and placeholders show values, so say "mark it visited", not "set it to '0'".
Expressions: variables by name, indexing [i], node fields .val .next .left .right, len(x),
old(x) for the value before the line ran, arithmetic + - * // %, comparisons, and/or/not.
cpp_lines maps each Python line that has an equivalent to the matching C++ line number.
"""


def visual_prompt(spec: dict, python_code: str, cpp_code: str, problem: str = "") -> str:
    def numbered(code: str) -> str:
        return "\n".join(f"{i:>3}| {line}" for i, line in enumerate(code.splitlines(), 1))

    text = (
        f"Problem: {spec.get('title', '')}\nInput: {json.dumps(spec.get('params', []))}\n"
        f"Returns: {spec.get('output', '')}\n\nPython (line numbers on the left):\n"
        f"{numbered(python_code)}\n\nC++:\n{numbered(cpp_code)}\n"
    )
    if problem:
        text += f"\nYour previous answer had these problems; fix them:\n{problem}\n"
    return text


def prompt_set_hash() -> str:
    """Part of the cache key: changing any prompt invalidates stored results."""
    blob = "\n".join(
        [
            PARSE_SYSTEM,
            BRUTE_A_SYSTEM,
            BRUTE_B_SYSTEM,
            APPROACHES_SYSTEM,
            REPAIR_SYSTEM,
            CHECKER_SYSTEM,
            CODE_RULES,
            SCHEMA_GUIDE,
            VISUAL_SYSTEM,
        ]
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
