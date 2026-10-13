"""Startup self-test. Until it passes, the sandbox reports unhealthy and refuses every batch.

It proves on *this* host, every time the service starts, that jails start, that both
languages run, and that the jail's key protections are actually in force. A host where
seccomp/AppArmor/namespaces behave differently fails here, loudly, instead of silently
running code with weaker isolation or turning sandbox faults into verdicts on code.
"""

from algolens_sandbox.batch import BatchRequest, PerTestLimits, TestCase, run_batch

PROBE_PY = """
import ctypes, os, socket
def arithmetic(a, b):
    return a + b
def unshare_user_ns():
    libc = ctypes.CDLL(None, use_errno=True)
    return "allowed" if libc.unshare(0x10000000) == 0 else "blocked"
def network():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1).close()
        return "reachable"
    except OSError:
        return "blocked"
def host_files():
    return "visible" if os.path.exists("/etc/passwd") else "hidden"
def burn():
    while True:
        pass
"""

PROBE_CPP = r"""
#include <algolens.h>
int main() { algolens::read_input(); algolens::emit("[1,2,3]"); }
"""

EXPECTED_PY = {
    "arithmetic": ("ok", 5),
    "unshare_user_ns": ("ok", "blocked"),
    "network": ("ok", "blocked"),
    "host_files": ("ok", "hidden"),
    "burn": ("timeout", None),
}


def run() -> list[str]:
    """Returns a list of problems; empty means the sandbox is safe to use."""
    problems = []
    for entry, (outcome, value) in EXPECTED_PY.items():
        args = [2, 3] if entry == "arithmetic" else []
        resp = run_batch(
            BatchRequest(
                language="python",
                source=PROBE_PY,
                entry=entry,
                tests=[TestCase(id="t", input={"args": args})],
                per_test=PerTestLimits(cpu_ms=300, wall_ms=2000),
                batch_wall_s=10,
            )
        )
        got = (resp.results[0].outcome, resp.results[0].value) if resp.results else None
        if resp.status != "ok" or got != (outcome, value):
            problems.append(f"python {entry}: expected {(outcome, value)}, got "
                            f"{resp.status} {got} {resp.detail}".strip())  # fmt: skip
    resp = run_batch(
        BatchRequest(language="cpp", source=PROBE_CPP, tests=[TestCase(id="t", input={})])
    )
    got = (resp.results[0].outcome, resp.results[0].value) if resp.results else None
    if resp.status != "ok" or got != ("ok", [1, 2, 3]):
        problems.append(f"c++: expected ok [1, 2, 3], got {resp.status} {got} "
                        f"{resp.detail} {resp.compile_output[-300:]}".strip())  # fmt: skip
    return problems
