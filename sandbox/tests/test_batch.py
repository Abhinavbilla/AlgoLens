"""Hostile-code and behaviour suite. Runs inside the sandbox image under production limits."""

import textwrap

import pytest
from algolens_sandbox import jail, selftest
from algolens_sandbox.batch import BatchRequest, PerTestLimits, run_batch
from algolens_sandbox.batch import TestCase as Case

FAST = PerTestLimits(cpu_ms=500, wall_ms=2000, mem_mb=128, output_bytes=64 << 10)


def py(source: str, entry: str, inputs: list[dict] | None = None, **kw):
    inputs = inputs if inputs is not None else [{"args": []}]
    tests = [Case(id=f"t{i}", input=inp) for i, inp in enumerate(inputs)]
    return run_batch(
        BatchRequest(language="python", source=textwrap.dedent(source), entry=entry,
                     tests=tests, per_test=kw.pop("per_test", FAST), **kw)
    )  # fmt: skip


def cpp(source: str, n_tests: int = 1, **kw):
    tests = [Case(id=f"t{i}", input={"i": i}) for i in range(n_tests)]
    return run_batch(
        BatchRequest(language="cpp", source=textwrap.dedent(source), tests=tests,
                     per_test=kw.pop("per_test", FAST), **kw)
    )  # fmt: skip


def only(resp):
    assert resp.status == "ok", resp
    assert len(resp.results) == 1
    return resp.results[0]


# --- the self-test the service runs on startup ---------------------------------------------


def test_selftest_passes_on_this_host():
    assert selftest.run() == []


# --- normal behaviour ---------------------------------------------------------------------


def test_python_returns_values_per_test():
    resp = py("def add(a, b):\n    return a + b\n", "add",
              [{"args": [1, 2]}, {"args": [10, -3]}, {"kwargs": {"a": 0, "b": 0}}])  # fmt: skip
    assert resp.status == "ok"
    assert [r.value for r in resp.results] == [3, 7, 0]
    assert all(r.outcome == "ok" for r in resp.results)


def test_tests_cannot_leak_state_into_each_other():
    resp = py("calls = []\ndef f():\n    calls.append(1)\n    return len(calls)\n", "f",
              [{"args": []}] * 5)  # fmt: skip
    assert [r.value for r in resp.results] == [1] * 5


def test_set_iteration_order_is_reproducible():
    src = "def f():\n    return list({'apple', 'kiwi', 'fig', 'date', 'plum'})\n"
    assert only(py(src, "f")).value == only(py(src, "f")).value


def test_deep_recursion_works():
    src = "def depth(n):\n    return 0 if n == 0 else 1 + depth(n - 1)\n"
    assert only(py(src, "depth", [{"args": [5000]}])).value == 5000


def test_solution_print_does_not_corrupt_result():
    r = only(py("def f():\n    print('noise', 42)\n    return 'real'\n", "f"))
    assert (r.value, r.stdout.strip()) == ("real", "noise 42")


def test_cpp_reads_input_and_emits_result():
    resp = cpp(
        """
        #include <algolens.h>
        #include <nlohmann/json.hpp>
        int main() {
            auto in = nlohmann::json::parse(algolens::read_input());
            std::cout << "noise\\n";
            algolens::emit(nlohmann::json({{"twice", in["i"].get<int>() * 2}}).dump());
        }
        """,
        n_tests=3,
    )
    assert resp.status == "ok", resp
    assert [r.value for r in resp.results] == [{"twice": 0}, {"twice": 2}, {"twice": 4}]


# --- outcome classification -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "outcome", "detail"),
    [
        ("def f():\n    raise ValueError('boom')\n", "runtime_error", "exit code 1"),
        ("def f():\n    while True:\n        pass\n", "timeout", "CPU time"),
        ("import time\ndef f():\n    time.sleep(30)\n", "timeout", "wall time"),
        ("def f():\n    x = []\n    while True:\n        x.append(bytearray(1 << 24))\n",
         "memory", "memory"),
        ("def f():\n    while True:\n        print('x' * 1000)\n", "output_limit", "output"),
        ("def f():\n    return 'x' * (1 << 20)\n", "output_limit", "output"),
        ("def f():\n    return object()\n", "runtime_error", "not JSON-serializable"),
        ("def f():\n    return float('nan')\n", "runtime_error", "not JSON-serializable"),
    ],
    ids=["exception", "cpu", "wall", "memory", "stdout-flood", "huge-result", "object", "nan"],
)  # fmt: skip
def test_python_outcomes(source, outcome, detail):
    r = only(py(source, "f"))
    assert r.outcome == outcome, r
    assert detail in r.detail, r


def test_exception_traceback_is_reported():
    r = only(py("def f():\n    raise KeyError('missing')\n", "f"))
    assert "KeyError" in r.stderr


def test_missing_entry_function_is_a_runtime_error():
    r = only(py("def g():\n    return 1\n", "f"))
    assert r.outcome == "runtime_error" and "AttributeError" in r.stderr


@pytest.mark.parametrize(
    ("body", "outcome"),
    [
        ("volatile int* p = nullptr; return *p;", "runtime_error"),
        ("std::vector<std::vector<char>> v; for (;;) v.emplace_back(1 << 24, 'x');", "memory"),
        ("volatile unsigned long n = 0; for (;;) ++n;", "timeout"),
        ("for (;;) std::cout << std::string(1000, 'x');", "output_limit"),
        ("return 0; /* never emits a result */", "runtime_error"),
    ],
    ids=["segfault", "bad_alloc", "cpu", "stdout-flood", "no-result"],
)
def test_cpp_outcomes(body, outcome):
    src = f"#include <algolens.h>\n#include <vector>\nint main() {{ {body} }}\n"
    r = only(cpp(src))
    assert r.outcome == outcome, r


def test_cpp_compile_error_is_reported_with_compiler_output():
    resp = cpp("int main() { return undefined_name; }\n")
    assert resp.status == "compile_error"
    assert "undefined_name" in resp.compile_output
    assert "/work/" not in resp.compile_output  # no sandbox paths leak into messages


@pytest.mark.parametrize("path", ["/etc/passwd", "/dev/zero", "/proc/self/environ",
                                  "/opt/algolens/app/algolens_sandbox/batch.py"])  # fmt: skip
def test_cpp_cannot_include_host_files(path):
    resp = cpp(f'#include "{path}"\nint main() {{}}\n')
    assert resp.status == "compile_error"


def test_batch_timeout_keeps_finished_results():
    src = "import time\ndef f(s):\n    time.sleep(s)\n    return s\n"
    resp = py(src, "f", [{"args": [0]}, {"args": [0.9]}, {"args": [0.9]}, {"args": [0.9]}],
              per_test=PerTestLimits(cpu_ms=500, wall_ms=1500), batch_wall_s=2)  # fmt: skip
    assert resp.status == "batch_timeout", resp
    assert resp.results[0].outcome == "ok"
    assert resp.results[-1].outcome == "not_run"


# --- containment ----------------------------------------------------------------------------


def test_network_is_unreachable():
    src = """
    import socket
    def f():
        out = []
        for host, port in [("1.1.1.1", 53), ("8.8.8.8", 443), ("db", 5432), ("api", 8000)]:
            try:
                socket.create_connection((host, port), timeout=1).close()
                out.append("REACHED " + host)
            except OSError:
                out.append("blocked")
        return out
    """
    assert only(py(src, "f")).value == ["blocked"] * 4


def test_container_and_host_files_are_invisible():
    src = """
    import os
    def f():
        paths = ["/etc/passwd", "/etc/hostname", "/proc/self/mounts", "/run/sandbox",
                 "/opt/algolens/app", "/jobs", "/home/sandbox"]
        return {"root": sorted(os.listdir("/")), "seen": [p for p in paths if os.path.exists(p)]}
    """
    r = only(py(src, "f"))
    assert r.value["seen"] == []
    assert set(r.value["root"]) <= {"bin", "driver", "etc", "lib", "lib64", "tmp", "usr", "work"}


def test_filesystem_is_read_only_except_small_tmp():
    src = """
    def f():
        out = {}
        for path in ["/usr/evil", "/work/evil", "/driver/driver.py", "/etc/ld.so.cache"]:
            try:
                open(path, "w").write("x")
                out[path] = "WRITABLE"
            except OSError:
                out[path] = "blocked"
        written = 0
        try:
            with open("/tmp/fill", "wb") as fh:
                while True:
                    fh.write(b"0" * (1 << 20)); fh.flush(); written += 1
        except OSError:
            pass
        out["tmp_mb"] = written
        return out
    """
    v = only(py(src, "f")).value
    assert [v[p] for p in ["/usr/evil", "/work/evil", "/driver/driver.py", "/etc/ld.so.cache"]] \
        == ["blocked"] * 4  # fmt: skip
    assert v["tmp_mb"] <= 16


def test_privileged_syscalls_are_blocked():
    src = """
    import ctypes, os
    def f():
        libc = ctypes.CDLL(None, use_errno=True)
        calls = {
            "unshare_user": lambda: libc.unshare(0x10000000),
            "unshare_net": lambda: libc.unshare(0x40000000),
            "setns": lambda: libc.setns(0, 0),
            "mount": lambda: libc.mount(b"none", b"/usr", b"tmpfs", 0, None),
            "chroot": lambda: libc.chroot(b"/"),
            "ptrace_attach_1": lambda: libc.ptrace(16, 1, 0, 0),
        }
        out = {k: ("ALLOWED" if fn() == 0 else "blocked") for k, fn in calls.items()}
        try:
            os.setuid(0); out["setuid0"] = "ALLOWED"
        except OSError:
            out["setuid0"] = "blocked"
        return out
    """
    v = only(py(src, "f")).value
    assert set(v.values()) == {"blocked"}, v


def test_solution_cannot_kill_the_driver():
    src = """
    import os, signal
    def f(i):
        if i == 0:
            for target in (1, -1, os.getppid()):
                try:
                    os.kill(target, signal.SIGKILL)
                except OSError:
                    pass
        return i
    """
    resp = py(src, "f", [{"args": [i]} for i in range(3)])
    assert resp.status == "ok", resp
    assert [r.value for r in resp.results] == [0, 1, 2]


def test_forged_result_message_is_rejected():
    src = """
    import os
    def f():
        os.write(3, b'{"value": "forged"}')
        return "real"
    """
    r = only(py(src, "f"))
    assert r.outcome == "runtime_error" and r.value is None


def test_fork_bomb_is_contained_and_next_test_runs():
    src = """
    import os, time
    def f(bomb):
        if bomb:
            n = 0
            try:
                while True:
                    if os.fork() == 0:
                        time.sleep(30); os._exit(0)
                    n += 1
            except OSError:
                return n
        return "fine"
    """
    resp = py(src, "f", [{"args": [True]}, {"args": [False]}])
    assert resp.results[0].outcome == "ok" and resp.results[0].value < 16
    assert (resp.results[1].outcome, resp.results[1].value) == ("ok", "fine")


def test_background_process_cannot_outlive_its_test():
    src = """
    import os, subprocess, time
    def f(first):
        if first:
            subprocess.Popen(["/usr/local/bin/python3", "-c", "import time; time.sleep(60)"],
                             start_new_session=True)
            return "spawned"
        return "next"
    """
    resp = py(src, "f", [{"args": [True]}, {"args": [False]}], batch_wall_s=20)
    assert resp.status == "ok", resp
    assert resp.results[1].value == "next"


# --- a broken sandbox must never produce verdicts --------------------------------------------


def test_jail_that_fails_to_start_is_a_sandbox_error(monkeypatch):
    monkeypatch.setattr(jail, "NSJAIL", "/bin/false")
    resp = py("def f():\n    return 1\n", "f")
    assert resp.status == "sandbox_error"
    assert resp.results == []
    resp = cpp("int main() {}\n")
    assert resp.status == "sandbox_error"


def test_python_batch_without_entry_is_refused():
    assert py("def f():\n    return 1\n", "").status == "sandbox_error"


def test_entry_must_be_an_identifier():
    with pytest.raises(ValueError):
        BatchRequest(language="python", source="", entry="f(); import os", tests=[])


def test_driver_setup_failure_is_a_sandbox_error_not_a_verdict(monkeypatch):
    # Fault injection: give the driver's jail a lower memory ceiling than the per-test limit
    # it must set, so its own setrlimit fails during setup, before any solution code runs.
    from algolens_sandbox import batch

    real = batch.jail.JailLimits
    monkeypatch.setattr(batch.jail, "JailLimits", lambda **kw: real(**{**kw, "mem_mb": 100}))
    python_src = "def f():\n    return 1\n"
    cpp_src = '#include <algolens.h>\nint main() { algolens::emit("1"); }\n'
    for resp in (py(python_src, "f"), cpp(cpp_src)):
        assert resp.status == "sandbox_error", resp
        assert resp.results == []
        assert "setup failed" in resp.detail


def test_solution_cannot_fake_a_sandbox_error():
    resp = py("import os\ndef f():\n    os._exit(70)\n", "f")
    assert resp.status == "ok"
    assert resp.results[0].outcome == "runtime_error"


def test_crashes_produce_no_core_dumps():
    # A crash must end promptly, without streaming a memory image to a dump helper.
    src = r"""
    #include <cstdlib>
    #include <sys/resource.h>
    #include <algolens.h>
    int main() {
        rlimit r;
        getrlimit(RLIMIT_CORE, &r);
        if (r.rlim_cur != 1) { algolens::emit("\"core dumps enabled\""); return 0; }
        std::abort();
    }
    """
    r = only(cpp(src))
    assert r.outcome == "runtime_error", r
    assert r.wall_ms < 1000, r


def test_precompiled_header_is_used(tmp_path):
    # Parsing nlohmann/json costs ~2.7 s per compile without the precompiled header (~1 s
    # with it), and a busy machine stretches that toward the limit. g++ -H marks a used
    # precompiled header with "!"; the flags must be exactly the sandbox's.
    import subprocess

    from algolens_sandbox.batch import CPP_FLAGS

    src = tmp_path / "t.cpp"
    src.write_text(
        "#include <algolens.h>\nint main() { algolens::emit(algolens::Json(1).dump()); }\n"
    )
    out = subprocess.run(["g++", *CPP_FLAGS, "-H", "-o", str(tmp_path / "t"), str(src)],
                         capture_output=True, text=True, check=True)  # fmt: skip
    assert "! /usr/local/include/algolens/algolens.h.gch" in out.stderr
    resp = cpp(src.read_text())
    assert resp.status == "ok" and resp.results[0].value == 1, resp


def test_compile_timeout_has_its_own_status(monkeypatch):
    from algolens_sandbox import batch

    tight = batch.jail.JailLimits(wall_s=1, cpu_s=1, mem_mb=1024, nproc=32, fsize_mb=64, tmp_mb=128)
    monkeypatch.setattr(batch, "COMPILE_LIMITS", tight)
    # Deep template recursion: slow to compile, but valid code.
    src = """
    template <int N> struct F { static constexpr long v = F<N - 1>::v + F<N - 2>::v; };
    template <> struct F<1> { static constexpr long v = 1; };
    template <> struct F<0> { static constexpr long v = 0; };
    #include <algolens.h>
    int main() { algolens::emit(std::to_string(F<899>::v)); }
    """
    resp = cpp(src)
    assert resp.status in ("compile_timeout", "compile_error"), resp
    if resp.status == "compile_error":
        pytest.skip("compiler finished or rejected the code within a second on this machine")


def test_wall_limit_is_enforced_on_a_monotonic_clock_and_leaves_nothing_running():
    # nsjail's own time limit uses the wall clock and misfires when the host clock steps
    # backwards (seen on WSL), so the runner enforces it. Killing nsjail must take the
    # jailed program down with it.
    import os
    import time

    src = "import time\ndef f():\n    time.sleep(60)\n"
    start = time.monotonic()
    resp = py(src, "f", per_test=PerTestLimits(cpu_ms=500, wall_ms=30_000), batch_wall_s=2)
    assert resp.status == "batch_timeout", resp
    assert time.monotonic() - start < 6
    time.sleep(0.5)
    leftovers = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as fh:
                    cmd = fh.read().replace(b"\0", b" ")
            except OSError:
                continue
            if b"driver.py" in cmd or b"nsjail" in cmd:
                leftovers.append(cmd.decode(errors="replace")[:80])
    assert leftovers == [], leftovers


# --- TreeNode / ListNode inputs ----------------------------------------------------------------


def test_trees_and_lists_arrive_as_nodes_and_return_as_lists():
    src = """
    def invert(root):
        if root:
            root.left, root.right = invert(root.right), invert(root.left)
        return root

    def reverse(head):
        prev = None
        while head:
            head.next, prev, head = prev, head, head.next
        return prev

    def depth(root):
        return 0 if root is None else 1 + max(depth(root.left), depth(root.right))
    """
    tree = py(src, "invert", [{"args": [[4, 2, 7, 1, 3, None, 9]]}, {"args": [[]]}],
              convert=["binary_tree"], convert_result="binary_tree")  # fmt: skip
    assert [r.value for r in tree.results] == [[4, 7, 2, 9, None, 3, 1], []]
    lst = py(src, "reverse", [{"args": [[1, 2, 3]]}], convert=["linked_list"])
    assert lst.results[0].value == [3, 2, 1]
    assert (
        only(py(src, "depth", [{"args": [[1, None, 2, None, 3]]}], convert=["binary_tree"])).value
        == 3
    )


def test_a_solution_may_define_its_own_node_class():
    src = """
    class TreeNode:
        def __init__(self, val=0, left=None, right=None):
            self.val, self.left, self.right = val, left, right
            self.mine = True
    def check(root):
        return root.mine
    """
    assert only(py(src, "check", [{"args": [[1]]}], convert=["binary_tree"])).value is True


def test_traced_tree_nodes_are_recorded_as_objects():
    from algolens_sandbox.batch import TraceRequest, run_trace

    src = "def first(root):\n    node = root.left\n    return node.val\n"
    resp = run_trace(TraceRequest(source=src, entry="first", input={"args": [[1, 2, 3]]},
                                  convert=["binary_tree"]))  # fmt: skip
    assert resp.status == "ok" and resp.value == 2
    heap = resp.trace["heap"]
    classes = {c.get("class") for c in heap.values()}
    assert "TreeNode" in classes
