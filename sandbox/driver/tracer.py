"""Line tracer for animations. Runs INSIDE the jail, in the child process with the solution.

Frame semantics (plan §7.2), pinned by sandbox/tests/test_tracer.py:
    A frame is one line that just finished running in some activation (function call), with
    the values *after* it ran. `line` is that line; `next` is the line the same activation
    runs next, or "return". A call made from a line does not finish that line: the callee's
    frames come first, and the caller's line finishes when control comes back to it.

settrace fires `line` *before* a line runs, so a line is known to have finished when the
next `line` or `return` event arrives for the same activation.

The recorder only observes. It never calls code from the solution (no __repr__, __eq__,
__hash__ or attribute hooks of user classes): containers are read through the builtin
types' own methods and objects through their __dict__. So recording can't change what the
code does; the sandbox also checks traced and untraced results match.

Values are encoded as JSON:
    scalars inline (ints beyond ±2^53 as {"int": "..."}, non-finite floats as {"float": ...})
    tuples inline as {"tuple": [...]}
    mutable objects by reference {"ref": n}: object n, numbered in first-seen order
    anything else as {"opaque": "<type name>"}

Each object's contents are stored once per distinct version in `heap` under "n.v". Each
frame has `objects`, mapping every object reachable in that frame to its version there, so
references (including cyclic ones) always resolve to exactly the state at that frame.
"""

import json
import sys
from collections import deque

MAX_ITEMS = 2000  # per container
MAX_OBJECTS = 5000  # reachable mutable objects per snapshot
MAX_STR = 1000
SAFE_INT = 2**53


class _Activation:
    __slots__ = ("aid", "fn", "frame", "params", "pending")

    def __init__(self, aid, fn, frame):
        self.aid = aid
        self.fn = fn
        self.frame = frame
        code = frame.f_code
        self.params = list(code.co_varnames[: code.co_argcount + code.co_kwonlyargcount])
        self.pending = None  # line started but not yet known to have finished


class SnapshotTooLarge(Exception):
    pass


class Recorder:
    def __init__(self, filename: str, max_frames: int = 5000):
        self.filename = filename
        self.max_frames = max_frames
        self.frames: list[dict] = []
        self.heap: dict[str, dict] = {}
        self.truncated: str | None = None
        self._objects: dict[int, tuple[object, int]] = {}  # id -> (obj kept alive, number)
        self._versions: dict[int, tuple[str, int]] = {}  # number -> (content json, version)
        self._by_frame: dict[int, _Activation] = {}
        self._stack: list[_Activation] = []
        self._next_aid = 0

    # --- tracing ---------------------------------------------------------------------------

    def start(self) -> None:
        sys.settrace(self._on_call)

    def stop(self) -> None:
        sys.settrace(None)

    def _on_call(self, frame, event, arg):
        if event != "call" or frame.f_code.co_filename != self.filename or self.truncated:
            return None
        act = _Activation(self._next_aid, frame.f_code.co_name, frame)
        self._next_aid += 1
        self._stack.append(act)
        self._by_frame[id(frame)] = act
        return self._on_event

    def _on_event(self, frame, event, arg):
        if self.truncated:
            return None
        act = self._by_frame.get(id(frame))
        if act is None:
            return None
        if event == "line":
            if act.pending is not None:
                self._emit(act, act.pending, frame.f_lineno)
            act.pending = frame.f_lineno
        elif event == "return":
            if act.pending is not None:
                self._emit(act, act.pending, "return", ret=(arg,))
            self._pop(act)
        elif event == "exception":
            # The pending line didn't finish normally. If the exception is caught here, the
            # handler's lines follow as usual; if not, a `return` event follows.
            if act.pending is not None:
                self._emit(act, act.pending, None, raised=arg[0].__name__)
                act.pending = None
        return self._on_event

    def _pop(self, act: _Activation) -> None:
        self._by_frame.pop(id(act.frame), None)
        if act in self._stack:
            self._stack.remove(act)

    # --- snapshots -------------------------------------------------------------------------

    def _emit(self, act, line, next_line, ret=None, raised=None) -> None:
        try:
            seen: dict[int, int | None] = {}  # object number -> version in this frame
            stack = []
            for a in self._stack:
                locals_ = {
                    name: self._encode(value, seen)
                    for name, value in a.frame.f_locals.items()
                    if not name.startswith("__")
                }
                stack.append(
                    {"aid": a.aid, "fn": a.fn, "params": a.params,
                     "line": line if a is act else a.pending,
                     "locals": locals_}
                )  # fmt: skip
            frame = {"line": line, "next": next_line, "aid": act.aid, "stack": stack}
            if ret is not None:
                frame["ret"] = self._encode(ret[0], seen)
            if raised is not None:
                frame["raised"] = raised
            frame["objects"] = {str(n): v for n, v in seen.items()}
        except SnapshotTooLarge:
            self._truncate("snapshot_too_large")
            return
        self.frames.append(frame)
        if len(self.frames) >= self.max_frames:
            self._truncate("too_many_frames")

    def _truncate(self, reason: str) -> None:
        self.truncated = reason
        sys.settrace(None)

    def _encode(self, v, seen: dict[int, int | None]):
        t = type(v)
        if v is None or t is bool:
            return v
        if t is int:
            return v if -SAFE_INT <= v <= SAFE_INT else {"int": str(v)}
        if t is float:
            if v != v or v in (float("inf"), float("-inf")):
                return {"float": repr(v)}
            return v
        if t is str:
            return v if len(v) <= MAX_STR else v[:MAX_STR] + "..."
        if t is tuple:
            return {"tuple": [self._encode(x, seen) for x in v[:MAX_ITEMS]]}
        if isinstance(v, list | dict | set | frozenset | deque) or _is_plain_object(v):
            return {"ref": self._ref(v, seen)}
        return {"opaque": t.__name__}

    def _ref(self, obj, seen: dict[int, int | None]) -> int:
        oid = id(obj)
        if oid not in self._objects:
            self._objects[oid] = (obj, len(self._objects))  # keeps it alive: ids stay unique
        number = self._objects[oid][1]
        if number in seen:  # shared or cyclic: refs are by number, so nothing more to do
            return number
        seen[number] = None
        if len(seen) > MAX_OBJECTS:
            raise SnapshotTooLarge
        content = self._content(obj, seen)
        encoded = json.dumps(content, sort_keys=True)
        previous = self._versions.get(number)
        if previous is None or previous[0] != encoded:
            version = 0 if previous is None else previous[1] + 1
            self._versions[number] = (encoded, version)
            self.heap[f"{number}.{version}"] = content
        seen[number] = self._versions[number][1]
        return number

    def _content(self, obj, seen: dict[int, int | None]) -> dict:
        if isinstance(obj, dict):
            items = list(dict.items(obj))
            if len(items) > MAX_ITEMS:
                raise SnapshotTooLarge
            body = [[self._encode(k, seen), self._encode(x, seen)] for k, x in items]
            return {"type": "dict", "class": type(obj).__name__, "items": body}
        if isinstance(obj, list | deque | set | frozenset):
            kind = {list: "list", deque: "deque", set: "set", frozenset: "frozenset"}
            base = next(b for b in (list, deque, set, frozenset) if isinstance(obj, b))
            items = list(base.__iter__(obj))
            if len(items) > MAX_ITEMS:
                raise SnapshotTooLarge
            return {"type": kind[base], "items": [self._encode(x, seen) for x in items]}
        fields = object.__getattribute__(obj, "__dict__")
        return {
            "type": "object",
            "class": type(obj).__name__,
            "fields": {
                k: self._encode(x, seen) for k, x in dict.items(fields) if not k.startswith("__")
            },  # fmt: skip
        }

    def result(self) -> dict:
        return {"frames": self.frames, "heap": self.heap, "truncated": self.truncated}


def _is_plain_object(v) -> bool:
    """Instances of classes defined by the solution (e.g. ListNode, TreeNode)."""
    t = type(v)
    if t.__module__ != "solution":
        return False
    try:
        object.__getattribute__(v, "__dict__")
    except AttributeError:
        return False
    return True
