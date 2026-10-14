"""Source check for code that will be animated (traced).

The tracer runs in the same process as the code it records, so code that reached for the
tracing machinery (sys.settrace, frame objects, ...) could stop or forge the recording. Code
to be traced is therefore limited to plain algorithmic Python: a small set of standard
library imports, and no access to tracing hooks, frames, introspection or dynamic code.

This guards the *integrity of the recording*. It isn't the security boundary (that's the
jail), and plain test batches don't need it.
"""

import ast

ALLOWED_IMPORTS = frozenset({
    "bisect", "collections", "dataclasses", "functools", "heapq", "itertools", "math",
    "operator", "string", "typing",
})  # fmt: skip
FORBIDDEN_NAMES = frozenset({
    "__import__", "breakpoint", "builtins", "compile", "ctypes", "delattr", "dir", "eval",
    "exec", "exit", "gc", "getattr", "globals", "help", "importlib", "input", "inspect",
    "locals", "memoryview", "open", "os", "quit", "setattr", "sys", "vars",
})  # fmt: skip
FORBIDDEN_ATTRS = frozenset({
    "_current_frames", "_getframe", "getprofile", "gettrace", "monitoring", "setprofile",
    "settrace",
})  # fmt: skip
FRAME_ATTR_PREFIXES = ("f_", "gi_", "cr_", "ag_", "tb_", "co_")


def check_traceable(source: str) -> list[str]:
    """Problems that make `source` unsafe to trace; empty means OK."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg} (line {exc.lineno})"]
    problems = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    problems.append(f"line {line}: import of {alias.name!r} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                problems.append(f"line {line}: import from {node.module!r} is not allowed")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or node.id.startswith("__"):
                problems.append(f"line {line}: use of {node.id!r} is not allowed")
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if (attr.startswith("__") or attr in FORBIDDEN_ATTRS
                    or attr.startswith(FRAME_ATTR_PREFIXES)):  # fmt: skip
                problems.append(f"line {line}: attribute {attr!r} is not allowed")
        elif isinstance(node, ast.alias) and node.asname and node.asname.startswith("__"):
            problems.append(f"line {line}: alias {node.asname!r} is not allowed")
    return problems
