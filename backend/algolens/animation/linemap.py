"""Which C++ line does the same job as each Python line (for highlighting both while the
animation plays).

Library entries have hand-made maps. Generated approaches get one computed here, without AI:
the two versions are written side by side and keep the same order, so the lines are aligned
like two sequences (as in a diff), scoring each pair by what they share: keywords (if, while,
return), operators, numbers and names. Names count as shared when one is a short form of the
other ("l" and "left", "h" and "height") and naming styles are ignored ("two_sum" and
"twoSum"). Lines stay in order, several Python lines may share one C++ line (C++ often puts
two statements on one line), and pairs that share too little are left out: an unmapped line
just keeps the previous highlight.
"""

import re
from collections import Counter

MIN_SCORE = 0.3

# Spelled differently in the two languages, but the same idea.
SYNONYMS = {
    "elif": ["else", "if"],
    "and": ["&&"],
    "or": ["||"],
    "not": ["!"],
    "true": ["true"],
    "false": ["false"],
    "none": ["null"],
    "nullptr": ["null"],
    "null": ["null"],
    "len": ["size"],
    "size": ["size"],
    "length": ["size"],
    "append": ["push"],
    "push_back": ["push"],
    "emplace_back": ["push"],
    "push": ["push"],
    "pop": ["pop"],
    "pop_back": ["pop"],
    "popleft": ["pop"],
    "pop_front": ["pop"],
    "def": ["fn"],
    "lambda": ["fn"],
    "self": [],
    "std": [],
    "const": [],
    "auto": [],
    "int": [],
    "long": [],
    "double": [],
    "bool": [],
    "string": [],
    "vector": [],
    "char": [],
    "unsigned": [],
    "static": [],
    "in": [],
    "range": [],
    "void": [],
    "return": ["return"],
    "break": ["break"],
    "continue": ["continue"],
    "float": [],
    "inf": ["inf"],
    "int_max": ["inf"],
    "llong_max": ["inf"],
    "numeric_limits": ["inf"],
    "max": ["max"],
    "min": ["min"],
    "sort": ["sort"],
    "sorted": ["sort"],
    "reverse": ["reverse"],
    "reversed": ["reverse"],
    "abs": ["abs"],
    "swap": ["swap"],
}
OPERATORS = {"+=": "+=", "++": "+=", "-=": "-=", "--": "-=", "==": "==", "!=": "!=",
             "<=": "<=", ">=": ">=", "<": "<", ">": ">", "//": "/", "/": "/", "%": "%",
             "*": "*", "+": "+", "-": "-", "=": "=", "[": "[", "&&": "&&", "||": "||",
             "!": "!"}  # fmt: skip
KEYWORDS = {"if", "else", "while", "for", "return", "break", "continue", "fn", "push", "pop",
            "size", "max", "min", "sort", "null", "true", "false", "&&", "||", "!", "inf",
            "swap", "abs", "reverse"}  # fmt: skip
_TOKEN = re.compile(r"[A-Za-z_]\w*|\d+|\+\+|--|\+=|-=|==|!=|<=|>=|&&|\|\||//|[-+*/%<>=!\[]")
_STRING = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")


def _tokens(line: str, comment: str) -> list[str]:
    line = _STRING.sub(" s ", line)
    if comment in line:
        line = line[: line.index(comment)]
    out: list[str] = []
    for t in _TOKEN.findall(line):
        if t in OPERATORS:
            out.append(OPERATORS[t])
            continue
        key = t.lower()
        if key in SYNONYMS:
            out += SYNONYMS[key]
        elif t[0].isdigit():
            out.append(t)
        else:
            out.append("$" + key.replace("_", ""))  # a name: case and underscores ignored
    return out


def _python(code: str) -> list[list[str]]:
    return [_tokens(line, "#") for line in code.splitlines()]


def _cpp(code: str) -> list[list[str]]:
    """Token lists per line, with the program's scaffolding (includes, main and everything
    after it) left empty so nothing maps there."""
    out: list[list[str]] = []
    in_main = False
    for line in code.splitlines():
        s = line.strip()
        if re.match(r"(int|auto)\s+main\s*\(", s):
            in_main = True
        if in_main or s.startswith(("#", "using ", "//", "namespace")) or not s.strip("{}; "):
            out.append([])
        else:
            out.append(_tokens(line, "//"))
    return out


def _same_name(a: str, b: str) -> bool:
    if a == b:
        return True
    short, long_ = sorted((a[1:], b[1:]), key=len)
    return len(long_) >= 3 and len(short) >= 1 and long_.startswith(short)


def _score(py: list[str], cpp: list[str]) -> float:
    """How much of the Python line's content the C++ line has (0..1)."""
    if not py or not cpp:
        return 0.0
    left = Counter(cpp)
    got = total = 0.0
    for t in py:
        weight = 2.0 if t in KEYWORDS else 1.0 if t.startswith("$") or t.isdigit() else 0.5
        total += weight
        match = t if left[t] > 0 else None
        if match is None and t.startswith("$"):
            match = next((c for c in left if c.startswith("$") and left[c] > 0
                          and _same_name(t, c)), None)  # fmt: skip
        if match is not None:
            left[match] -= 1
            got += weight
    # A C++ line with much more in it than the Python line is a weaker match.
    extra = max(0, len(cpp) - 2 * len(py)) / max(len(cpp), 1)
    return got / total * (1 - 0.5 * extra)


def _py_functions(code: str) -> list[tuple[str, list[int]]]:
    """(function name, its own line indices) for each def, nested ones separately; lines
    outside every function are under ""."""
    blocks: dict[int, tuple[str, list[int]]] = {-1: ("", [])}
    stack: list[tuple[int, int]] = []  # (indent of the def line, block id)
    for i, line in enumerate(code.splitlines()):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        m = re.match(r"\s*def\s+(\w+)", line)
        if m:
            blocks[i] = (m.group(1), [i])
            stack.append((indent, i))
        else:
            blocks[stack[-1][1] if stack else -1][1].append(i)
    return list(blocks.values())


_CPP_FN = re.compile(
    r"(\w+)\s*(?:=\s*\[[^\]]*\]\s*)?\([^;]*\)\s*(?:->\s*[\w:<>]+\s*)?(?:const\s*)?\{"
)


def _cpp_functions(code: str) -> list[tuple[str, list[int]]]:
    """The same for C++: top-level functions and lambdas stored in a name, by brace depth."""
    blocks: dict[int, tuple[str, list[int]]] = {-1: ("", [])}
    stack: list[tuple[int, int]] = []  # (brace depth outside the function, block id)
    depth = 0
    for i, line in enumerate(code.splitlines()):
        s = _STRING.sub('""', line.split("//")[0])
        m = _CPP_FN.search(s)
        name = m.group(1) if m and m.group(1) not in ("if", "while", "for", "switch") else None
        if name:
            blocks[i] = (name, [i])
            stack.append((depth, i))
        else:
            blocks[stack[-1][1] if stack else -1][1].append(i)
        depth += s.count("{") - s.count("}")
        while stack and depth <= stack[-1][0] and not (name and stack[-1][1] == i):
            stack.pop()
    return list(blocks.values())


def align(python_code: str, cpp_code: str) -> dict[int, int]:
    """{python line: C++ line}, both 1-based, for the lines that clearly correspond.
    Functions are paired by name first (C++ defines helpers before their callers, Python
    often after or inside), then the lines within each pair are aligned in order."""
    py, cpp = _python(python_code), _cpp(cpp_code)
    py_fns, cpp_fns = _py_functions(python_code), _cpp_functions(cpp_code)
    used: set[int] = set()
    rest_py: list[int] = []
    out: dict[int, int] = {}
    for name, lines in py_fns:
        key = "$" + name.lower().replace("_", "")
        match = next((k for k, (n, _) in enumerate(cpp_fns) if k not in used and n
                      and ("$" + n.lower().replace("_", "")) == key), None)  # fmt: skip
        if name and match is not None:
            used.add(match)
            out.update(_align_lines(py, cpp, lines, cpp_fns[match][1]))
        else:
            rest_py += lines
    rest_cpp = sorted(j for k, (_, ls) in enumerate(cpp_fns) if k not in used for j in ls)
    out.update(_align_lines(py, cpp, sorted(rest_py), rest_cpp))
    return dict(sorted(out.items()))


def _align_lines(py: list[list[str]], cpp: list[list[str]], pi: list[int],
                 cj: list[int]) -> dict[int, int]:  # fmt: skip
    """Aligns the Python lines `pi` with the C++ lines `cj` (indices, in order)."""
    n, m = len(pi), len(cj)
    if not n or not m:
        return {}
    s = [[_score(py[pi[i]], cpp[cj[j]]) for j in range(m)] for i in range(n)]
    # best[i][j]: best total for python lines i.. given C++ lines j.. are still available.
    # A Python line either matches C++ line j (and the next Python line may match j too, or
    # later), or is skipped; a C++ line can be skipped.
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    move = [[0] * (m + 1) for _ in range(n + 1)]  # 0 skip py, 1 skip cpp, 2 match
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            options = [(best[i + 1][j], 0), (best[i][j + 1], 1)]
            if s[i][j] >= MIN_SCORE:
                options.append((s[i][j] + best[i + 1][j], 2))
            best[i][j], move[i][j] = max(options)
    out: dict[int, int] = {}
    i = j = 0
    while i < n and j < m:
        if move[i][j] == 2:
            out[pi[i] + 1] = cj[j] + 1
            i += 1
        elif move[i][j] == 1:
            j += 1
        else:
            i += 1
    return out
