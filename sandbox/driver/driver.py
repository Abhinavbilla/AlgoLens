"""Batch test driver. Runs INSIDE the jail as PID 1; standard library only.

Reads /work/request.json and runs each test in its own forked child with per-test CPU,
wall-time, memory and output limits, writing one JSON line per finished test to stdout.

Safety properties this file is responsible for:
- The parent never imports or calls solution code, so solution code can't alter it.
- Each test runs in a fresh child, so state can't leak from one test into the next.
- As PID 1 of the jail's PID namespace, the parent ignores signals from its children
  (the kernel drops SIGKILL to a namespace init from inside the namespace).
- A child can only report through its own result pipe (fd 3); the parent accepts exactly
  one well-formed message per child and treats anything else as a runtime error.
- A failure in the driver's own per-test setup is reported as `setup_error`, never as a
  verdict on the solution. Setup success is signalled on a separate pipe that is written
  and closed before any solution code runs, so solution code can't fake it.
"""

import contextlib
import json
import math
import os
import resource
import select
import signal
import sys
import time
import traceback

REQUEST = "/work/request.json"
PY_SOLUTION = "/work/solution.py"
CPP_BINARY = "/work/a.out"
CPP_INPUT = "/tmp/input.json"
DRIVER_DIR = "/driver"
EXIT_MEMORY = 86  # Python child hit MemoryError
EXIT_UNSERIALIZABLE = 87  # Python child returned something that isn't JSON
READY = b"R"  # child setup done; solution code (or the C++ exec) is about to run
EXEC_FAILED = b"E"  # C++ child: execv failed after READY
LOG_CAP = 8 << 10  # stdout/stderr kept per test (for debugging; never judged)
POLL_S = 0.005  # how often to check whether the test's process has exited


def disable_core_dumps() -> None:
    """No crash dumps from anything in the jail. RLIMIT_CORE == 1 byte is the kernel's
    special value that also suppresses dumps piped to a helper (core_pattern "|..."), which
    a limit of 0 does not. On WSL every crash would otherwise stream its memory image to
    /wsl-capture-crash: slow, host-dependent timing, and dump files on the host's disk.
    Inherited by every child and kept across exec."""
    resource.setrlimit(resource.RLIMIT_CORE, (1, 1))


def main() -> None:
    disable_core_dumps()
    if len(sys.argv) > 2 and sys.argv[1] == "--exec":
        # Exec wrapper for other jailed tools (the compiler) so they get the same setting.
        os.execv(sys.argv[2], sys.argv[2:])
    with open(REQUEST) as f:
        req = json.load(f)
    per = req["per_test"]
    for test in req["tests"]:
        result = run_one(req["language"], req.get("entry", ""), test,
                         {**per, "convert": req.get("convert") or [],
                          "convert_result": req.get("convert_result")})  # fmt: skip
        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()


def _kill_leftovers() -> None:
    """Kill every other process in the jail, then reap them, so nothing a test started
    (even in its own session or process group) survives into the next test.

    Only safe as PID 1 of the jail's own PID namespace, where kill(-1) reaches exactly the
    jail's processes. Anywhere else it would signal everything this user owns, so refuse.
    """
    if os.getpid() != 1:
        return
    with contextlib.suppress(ProcessLookupError):
        os.kill(-1, signal.SIGKILL)
    while True:
        try:
            os.waitpid(-1, 0)
        except ChildProcessError:
            return


def run_one(language: str, entry: str, test: dict, per: dict) -> dict:
    if language == "cpp":
        with open(CPP_INPUT, "w") as f:
            json.dump(test["input"], f)
    res_r, res_w = os.pipe()
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    ready_r, ready_w = os.pipe()
    start = time.monotonic()
    pid = os.fork()
    if pid == 0:  # child: never returns
        try:
            _child(language, entry, test, per, res_w, out_w, err_w, ready_w)
        finally:
            os._exit(70)
    with contextlib.suppress(OSError):  # also done in the child; whichever runs first wins
        os.setpgid(pid, pid)
    for fd in (res_w, out_w, err_w, ready_w):
        os.close(fd)

    wall_limit = per["wall_ms"] / 1000
    traced = bool(test.get("trace"))
    counted = bool(test.get("count")) and not traced and language == "python"
    out_cap = per["output_bytes"]
    res_cap = per["trace_output_bytes"] if traced else out_cap
    bufs = {res_r: bytearray(), out_r: bytearray(), err_r: bytearray(), ready_r: bytearray()}
    sizes = dict.fromkeys(bufs, 0)
    open_fds = set(bufs)

    def read_ready(timeout: float) -> bool:
        """Read whatever is ready within `timeout`. Returns False if nothing was ready."""
        if not open_fds:
            time.sleep(timeout)
            return False
        ready, _, _ = select.select(list(open_fds), [], [], timeout)
        for fd in ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                open_fds.discard(fd)
                continue
            sizes[fd] += len(chunk)
            keep = res_cap + 1 if fd == res_r else LOG_CAP
            if len(bufs[fd]) < keep:
                bufs[fd].extend(chunk[: keep - len(bufs[fd])])
        return bool(ready)

    # A test is over when its own process exits, even if leftover processes it started
    # still hold the pipes open; those leftovers are killed before the next test.
    exited = None
    killed_for = None
    while exited is None:
        remaining = start + wall_limit - time.monotonic()
        if remaining <= 0:
            killed_for = "wall"
            break
        read_ready(min(remaining, POLL_S))
        if sizes[res_r] > res_cap or sizes[out_r] > out_cap:
            killed_for = "output"
            break
        wpid, status, usage = os.wait4(pid, os.WNOHANG)
        if wpid == pid:
            exited = (status, usage)
    if exited:
        # Collect what the test wrote before exiting (bounded: leftovers may keep writing).
        for _ in range(64):
            if not read_ready(0):
                break
        if sizes[res_r] > res_cap or sizes[out_r] > out_cap:
            killed_for = "output"
    else:
        for kill in (lambda: os.killpg(pid, signal.SIGKILL), lambda: os.kill(pid, signal.SIGKILL)):
            with contextlib.suppress(ProcessLookupError):
                kill()
        _, status, usage = os.wait4(pid, 0)
        exited = (status, usage)
    status, usage = exited
    _kill_leftovers()
    for fd in bufs:
        os.close(fd)
    wall_ms = round((time.monotonic() - start) * 1000, 1)
    cpu_ms = round((usage.ru_utime + usage.ru_stime) * 1000, 1)

    ready = bytes(bufs[ready_r])
    setup_ok = ready == READY
    if not setup_ok:
        outcome, value, detail, trace = (
            "setup_error", None, f"driver setup failed ({ready!r})", None
        )  # fmt: skip
    else:
        outcome, value, detail, trace = _classify(
            language, status, killed_for, cpu_ms, per, bytes(bufs[res_r]), bytes(bufs[err_r]),
            traced, counted,
        )  # fmt: skip
    result = {
        "id": test["id"],
        "outcome": outcome,
        "value": value,
        "detail": detail,
        "cpu_ms": cpu_ms,
        "wall_ms": wall_ms,
        "stdout": bufs[out_r][:LOG_CAP].decode(errors="replace"),
        "stderr": bufs[err_r][:LOG_CAP].decode(errors="replace"),
    }
    if traced:
        result["trace"] = trace
    if counted:
        result["ops"] = trace["ops"] if trace else None
    return result


def _classify(language, status, killed_for, cpu_ms, per, result, stderr, traced, counted=False):
    if killed_for == "output":
        return "output_limit", None, f"output exceeded {per['output_bytes']} bytes", None
    if killed_for == "wall":
        return "timeout", None, f"wall time exceeded {per['wall_ms']} ms", None
    if os.WIFSIGNALED(status):
        sig = os.WTERMSIG(status)
        if sig in (signal.SIGPROF, signal.SIGXCPU) or cpu_ms >= per["cpu_ms"]:
            return "timeout", None, f"CPU time exceeded {per['cpu_ms']} ms", None
        if language == "cpp" and b"bad_alloc" in stderr:
            return "memory", None, f"memory exceeded {per['mem_mb']} MB", None
        return "runtime_error", None, f"killed by {signal.Signals(sig).name}", None
    code = os.WEXITSTATUS(status)
    if code == EXIT_MEMORY or (language == "cpp" and b"bad_alloc" in stderr):
        return "memory", None, f"memory exceeded {per['mem_mb']} MB", None
    if code == EXIT_UNSERIALIZABLE:
        return "runtime_error", None, "return value is not JSON-serializable", None
    if code != 0:
        return "runtime_error", None, f"exit code {code}", None
    try:
        message = json.loads(result.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "runtime_error", None, "no valid result was produced", None
    if language == "python":
        expected = {"value", "trace"} if traced else {"value", "ops"} if counted else {"value"}
        if not isinstance(message, dict) or set(message) != expected:
            return "runtime_error", None, "malformed result message", None
        if counted:
            return "ok", message["value"], "", {"ops": message["ops"]}
        return "ok", message["value"], "", message.get("trace")
    return "ok", message, "", None


def _count_lines(fn, args, kwargs) -> dict:
    """Run fn counting executed lines of the solution with sys.monitoring (plan §7.6), with
    the same definition as the tracer's frames: settrace reports a line when a new line
    starts *and* when a backward jump lands on the line it came from (a loop on one line,
    e.g. a comprehension), as CPython 3.12's legacy_tracing.c does. Events in any other
    code (the prelude, the standard library) are switched off at their first occurrence."""
    mon = sys.monitoring
    tool = mon.PROFILER_ID
    mon.use_tool_id(tool, "algolens-count")
    count = 0
    lines: dict = {}

    def line_of(code, offset):
        table = lines.get(code)
        if table is None:
            table = lines[code] = list(code.co_lines())
        for start, end, line in table:
            if start <= offset < end:
                return line
        return None

    def on_line(code, line):
        nonlocal count
        if code.co_filename == PY_SOLUTION:
            count += 1
            return None
        return mon.DISABLE

    def on_jump(code, source, destination):
        nonlocal count
        if code.co_filename != PY_SOLUTION or destination > source:
            return mon.DISABLE
        line = line_of(code, destination)
        if line is None or line != line_of(code, source):
            return mon.DISABLE  # handled by the LINE event at the destination
        count += 1
        return None

    mon.register_callback(tool, mon.events.LINE, on_line)
    mon.register_callback(tool, mon.events.JUMP, on_jump)
    mon.set_events(tool, mon.events.LINE | mon.events.JUMP)
    try:
        value = fn(*args, **kwargs)
    finally:
        mon.set_events(tool, 0)
        mon.register_callback(tool, mon.events.LINE, None)
        mon.register_callback(tool, mon.events.JUMP, None)
        mon.free_tool_id(tool)
    return {"value": value, "ops": count}


PRELUDE = """
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
"""
MAX_NODES = 100_000


def _structures_in(module, args: list, kinds: list) -> list:
    """Turn JSON arguments into TreeNode/ListNode where the input schema says so:
    binary trees arrive in level order (null for gaps), linked lists as plain lists."""
    out = []
    for i, a in enumerate(args):
        kind = kinds[i] if i < len(kinds) else None
        if kind == "binary_tree":
            out.append(_build_tree(module.TreeNode, a))
        elif kind == "linked_list":
            head = None
            for v in reversed(a):
                head = module.ListNode(v, head)
            out.append(head)
        else:
            out.append(a)
    return out


def _build_tree(cls, items: list):
    if not items:
        return None
    root = cls(items[0])
    queue, i = [root], 1
    while queue and i < len(items):
        node = queue.pop(0)
        for side in ("left", "right"):
            if i < len(items) and items[i] is not None:
                child = cls(items[i])
                setattr(node, side, child)
                queue.append(child)
            i += 1
    return root


def _structures_out(module, value, kind=None):
    """A returned TreeNode/ListNode becomes level order / a list again, for comparison. If the
    result is declared a tree or list, None is the empty one: []."""
    if value is None and kind in ("binary_tree", "linked_list"):
        return []
    tree_cls, list_cls = getattr(module, "TreeNode", None), getattr(module, "ListNode", None)
    if list_cls and isinstance(value, list_cls):
        out, node = [], value
        while node is not None and len(out) < MAX_NODES:
            out.append(node.val)
            node = node.next
        return out
    if tree_cls and isinstance(value, tree_cls):
        out, queue = [], [value]
        while queue and len(out) < MAX_NODES:
            node = queue.pop(0)
            out.append(None if node is None else node.val)
            if node is not None:
                queue += [node.left, node.right]
        while out and out[-1] is None:
            out.pop()
        return out
    return value


def _child(language, entry, test, per, res_w, out_w, err_w, ready_w) -> None:
    traced = bool(test.get("trace"))
    os.setpgid(0, 0)
    if language == "cpp":
        os.dup2(os.open(CPP_INPUT, os.O_RDONLY), 0)
    else:
        empty_r, empty_w = os.pipe()  # stdin at EOF (the jail has no /dev/null)
        os.close(empty_w)
        os.dup2(empty_r, 0)
    os.dup2(out_w, 1)
    os.dup2(err_w, 2)
    os.dup2(res_w, 3)
    os.dup2(ready_w, 4)
    os.closerange(5, 1024)  # nothing else of the parent's is reachable

    mem = per["mem_mb"] << 20
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    hard_cpu = math.ceil(per["cpu_ms"] / 1000) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (hard_cpu, hard_cpu))
    # Precise per-test CPU limit: SIGPROF's default action terminates the process.
    # Interval timers survive execve, so this also covers the C++ binary.
    signal.setitimer(signal.ITIMER_PROF, per["cpu_ms"] / 1000)

    if language == "cpp":
        os.write(4, READY)
        os.set_inheritable(4, False)  # closed by a successful exec; still open if it fails
        try:
            os.execv(CPP_BINARY, [CPP_BINARY])
        except OSError:
            os.write(4, EXEC_FAILED)
            os._exit(71)

    sys.setrecursionlimit(100_000)
    counting = bool(test.get("count")) and not traced
    recorder = None
    if traced:
        # Loaded before any solution code runs (part of setup, so a failure is ours).
        sys.path.insert(0, DRIVER_DIR)
        from tracer import Recorder

        recorder = Recorder(PY_SOLUTION, max_frames=per["max_frames"])
    os.write(4, READY)
    os.close(4)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("solution", PY_SOLUTION)
        module = importlib.util.module_from_spec(spec)
        # TreeNode/ListNode, as on LeetCode. Defined inside the solution module (so the
        # tracer records them like the solution's own objects); a solution may redefine them.
        exec(compile(PRELUDE, "<algolens prelude>", "exec"), module.__dict__)
        spec.loader.exec_module(module)
        args = _structures_in(module, test["input"].get("args", []), per.get("convert") or [])
        kwargs = test["input"].get("kwargs", {})
        fn = getattr(module, entry)
        if counting:
            ops = _count_lines(fn, args, kwargs)
            value = ops.pop("value")
        elif recorder:
            recorder.start()
            try:
                value = fn(*args, **kwargs)
            finally:
                recorder.stop()
        else:
            value = fn(*args, **kwargs)
    except MemoryError:
        os._exit(EXIT_MEMORY)
    except BaseException:
        sys.stderr.write(traceback.format_exc()[-4000:])
        sys.stderr.flush()
        os._exit(1)
    try:
        message = {"value": _structures_out(module, value, per.get("convert_result"))}
        if counting:
            message["ops"] = ops["ops"]
        if recorder:
            if test.get("trace") == "summary":  # integrity checks: the recording isn't needed
                message["trace"] = {"frames": len(recorder.frames), "truncated": recorder.truncated}
            else:
                message["trace"] = recorder.result()
        payload = json.dumps(message, allow_nan=False).encode()
    except (TypeError, ValueError):
        os._exit(EXIT_UNSERIALIZABLE)
    except MemoryError:
        os._exit(EXIT_MEMORY)
    sys.stdout.flush()
    view = memoryview(payload)
    while view:
        view = view[os.write(3, view) :]
    os._exit(0)


if __name__ == "__main__":
    main()
