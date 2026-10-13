"""M1 spike: run benign and hostile programs under nsjail and check each is contained.

Prints one line per case and a JSON summary; exits non-zero if any case is not contained.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

CASES = Path(__file__).parent / "cases"
JOBS = Path(os.environ.get("SPIKE_JOBS_DIR", "/jobs"))  # exec-enabled tmpfs; /tmp is noexec
OUTPUT_CAP = 1 << 20  # 1 MiB of stdout

# Seccomp filter for the jailed program itself (kafel syntax), on top of the container's.
# kafel's amd64 table predates some syscalls, so those use raw x86-64 numbers:
# 425-427 = io_uring_setup/enter/register, 435 = clone3 (ENOSYS so glibc falls back to clone);
# kafel calls umount2 "umount".
# The container profile has to allow namespace syscalls so nsjail can build the jail;
# this takes them away again from the code inside it.
CLONE_NAMESPACE_FLAGS = 0x7E020000  # CLONE_NEWNS|NEWCGROUP|NEWUTS|NEWIPC|NEWUSER|NEWPID|NEWNET
CHILD_SECCOMP = f"""
POLICY algolens {{
  ERRNO(1) {{
    unshare, setns, mount, umount, pivot_root, chroot, ptrace,
    process_vm_readv, process_vm_writev, bpf, perf_event_open, userfaultfd,
    SYSCALL[425], SYSCALL[426], SYSCALL[427],
    keyctl, add_key, request_key, kexec_load, kexec_file_load,
    init_module, finit_module, delete_module, open_by_handle_at, name_to_handle_at,
    acct, swapon, swapoff, reboot, settimeofday, clock_settime, mknod, mknodat,
    clone(flags) {{ (flags & {CLONE_NAMESPACE_FLAGS:#x}) != 0 }}
  }},
  ERRNO(38) {{ SYSCALL[435] }}
}}
USE algolens DEFAULT ALLOW
"""


@dataclass
class Limits:
    wall_s: int = 3
    cpu_s: int = 2
    mem_mb: int = 256
    nproc: int = 16
    fsize_mb: int = 16
    tmp_mb: int = 16


@dataclass
class Result:
    exit_code: int | None
    elapsed_s: float
    cpu_s: float
    stdout: str
    stderr: str
    nsjail_log: str
    output_capped: bool = False
    outcome: str = ""


def jail_cmd(argv: list[str], work: Path, limits: Limits, writable_work: bool, log: Path) -> list[str]:
    return [
        "nsjail", "--mode", "o", "--log", str(log),
        # Empty tmpfs root; only these mounts exist inside.
        "-R", "/usr", "-R", "/lib", "-R", "/lib64", "-R", "/bin", "-R", "/etc/ld.so.cache",
        ("-B" if writable_work else "-R"), f"{work}:/work",
        "-m", f"none:/tmp:tmpfs:size={limits.tmp_mb << 20}",
        "--cwd", "/work", "--hostname", "jail", "--disable_proc",
        "--user", "99999", "--group", "99999",
        "--time_limit", str(limits.wall_s),
        "--rlimit_cpu", str(limits.cpu_s),
        "--rlimit_as", str(limits.mem_mb),
        "--rlimit_fsize", str(limits.fsize_mb),
        "--rlimit_nproc", str(limits.nproc),
        "--rlimit_nofile", "64",
        "--rlimit_stack", "64",
        "--env", "PATH=/usr/local/bin:/usr/bin:/bin", "--env", "HOME=/tmp",
        "--seccomp_string", CHILD_SECCOMP,
        "--", *argv,
    ]  # fmt: skip


def run_jailed(argv: list[str], work: Path, limits: Limits, writable_work: bool = False) -> Result:
    log = work.parent / f"nsjail-{time.monotonic_ns()}.log"
    cmd = jail_cmd(argv, work, limits, writable_work, log)
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    # Backstop in case nsjail itself hangs: its own --time_limit should always fire first.
    watchdog = threading.Timer(limits.wall_s + 5, lambda: _kill_group(proc.pid))
    watchdog.start()
    out, capped = bytearray(), False
    while chunk := proc.stdout.read1(65536):
        out += chunk
        if len(out) > OUTPUT_CAP:
            capped = True
            _kill_group(proc.pid)
            break
    err = proc.stderr.read(65536)
    # wait4 gives CPU time including the jailed child, which nsjail reaps.
    _, status, usage = os.wait4(proc.pid, 0)
    proc.returncode = os.waitstatus_to_exitcode(status)
    watchdog.cancel()
    elapsed = time.monotonic() - start
    return Result(
        exit_code=proc.returncode,
        elapsed_s=round(elapsed, 2),
        cpu_s=round(usage.ru_utime + usage.ru_stime, 2),
        stdout=out[:4000].decode(errors="replace"),
        stderr=err[:4000].decode(errors="replace"),
        nsjail_log=log.read_text(errors="replace")[-3000:] if log.exists() else "",
        output_capped=capped,
    )


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def sandbox_failed(r: Result) -> bool:
    """True unless nsjail's log shows it actually started the program."""
    log = r.nsjail_log
    started = "Executing '" in log
    return not started or "Launching child process failed" in log


def classify(r: Result, limits: Limits) -> str:
    log, err = r.nsjail_log, r.stderr
    # nsjail failing to start the program must never look like the program's own failure.
    if sandbox_failed(r):
        return "sandbox_error"
    if r.output_capped:
        return "output_limit"
    if "run time >= time limit" in log or r.elapsed_s >= limits.wall_s:
        return "timeout"
    # RLIMIT_CPU with soft == hard kills with SIGKILL, so judge by CPU actually used.
    if r.cpu_s >= limits.cpu_s * 0.95 or r.exit_code == 128 + signal.SIGXCPU:
        return "timeout"
    if "MemoryError" in err or "bad_alloc" in err:
        return "memory"
    if r.exit_code == 0:
        return "ok"
    return "runtime_error"


@dataclass
class Case:
    name: str
    file: str
    expect: str  # outcome class
    stdout_has: list[str] = field(default_factory=list)
    stdout_lacks: list[str] = field(default_factory=list)
    limits: Limits = field(default_factory=Limits)


CASES_TO_RUN = [
    Case("python runs", "hello.py", "ok", ["hello from python 3.12"]),
    Case("c++ compiles and runs", "hello.cpp", "ok", ["hello from c++ 123"]),
    Case("network blocked", "network.py", "ok", ["blocked 1.1.1.1"], ["REACHED"]),
    Case("host files hidden", "host_files.py", "ok", ["blocked /etc/passwd"],
         ["READABLE", "WRITABLE"]),
    Case("cpu limit", "cpu_burn.py", "timeout"),
    Case("wall-time limit", "sleep_forever.py", "timeout"),
    Case("python memory limit", "mem_balloon.py", "memory"),
    Case("c++ memory limit", "mem_balloon.cpp", "memory"),
    Case("fork bomb contained", "fork_bomb.py", "ok", ["fork blocked after"]),
    Case("output limit", "output_flood.py", "output_limit"),
    Case("disk fill contained", "disk_fill.py", "ok", ["blocked after"]),
    Case("c++ segfault", "null_deref.cpp", "runtime_error"),
    Case("privilege escape blocked", "escape.py", "ok",
         ["blocked mount", "still here after kill -1"], ["ALLOWED"]),
]  # fmt: skip


def run_case(case: Case, root: Path) -> tuple[bool, Result]:
    job = Path(tempfile.mkdtemp(dir=root))
    work = job / "work"
    work.mkdir()
    src = CASES / case.file
    shutil.copy(src, work / src.name)
    if src.suffix == ".cpp":
        compile_limits = Limits(wall_s=30, cpu_s=30, mem_mb=1024, nproc=32, fsize_mb=64, tmp_mb=128)
        c = run_jailed(
            ["/usr/bin/g++", "-std=c++17", "-O2", "-o", "/work/a.out", f"/work/{src.name}"],
            work, compile_limits, writable_work=True,
        )  # fmt: skip
        if sandbox_failed(c):
            c.outcome = "sandbox_error"
            return False, c
        if c.exit_code != 0:
            c.outcome = "compile_error"
            return case.expect == "compile_error", c
        argv = ["/work/a.out"]
    else:
        argv = ["/usr/local/bin/python3", "-I", f"/work/{src.name}"]
    r = run_jailed(argv, work, case.limits)
    r.outcome = classify(r, case.limits)
    ok = (
        r.outcome == case.expect
        and all(s in r.stdout for s in case.stdout_has)
        and not any(s in r.stdout for s in case.stdout_lacks)
    )
    return ok, r


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="spike-", dir=JOBS))
    print(f"nsjail spike: uid={os.getuid()} python={sys.version.split()[0]}", flush=True)
    results, failures = [], 0
    for case in CASES_TO_RUN:
        ok, r = run_case(case, root)
        failures += not ok
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {case.name:<26} expected={case.expect:<13} got={r.outcome:<13} "
              f"exit={r.exit_code} {r.elapsed_s}s", flush=True)  # fmt: skip
        print("      out:", r.stdout.strip().replace("\n", " | ")[:220])
        if not ok:
            print("      stdout:", r.stdout[-800:].replace("\n", "\n              "))
            print("      stderr:", r.stderr[-800:].replace("\n", "\n              "))
            print("      nsjail:", r.nsjail_log[-600:].replace("\n", "\n              "))
        results.append({"case": case.name, "pass": ok, **asdict(r)})
    print(f"\n{len(CASES_TO_RUN) - failures}/{len(CASES_TO_RUN)} contained")
    Path("/tmp/spike-results.json").write_text(json.dumps(results, indent=2))
    return 1 if failures else 0


if __name__ == "__main__" and not os.environ.get("SPIKE_CONCURRENCY"):
    sys.exit(main())


def concurrency_check() -> bool:
    """Does a fork bomb in one jail starve a different jail running at the same time?"""
    root = Path(tempfile.mkdtemp(prefix="conc-", dir=JOBS))
    jobs = {}
    for name in ["fork_hold.py", "needs_forks.py"]:
        work = root / name / "work"
        work.mkdir(parents=True)
        shutil.copy(CASES / name, work / name)
        jobs[name] = work
    limits = Limits(wall_s=10, cpu_s=5)
    results = {}
    bomb = threading.Thread(
        target=lambda: results.__setitem__("bomb", run_jailed(
            ["/usr/local/bin/python3", "-I", "/work/fork_hold.py"], jobs["fork_hold.py"], limits)))
    bomb.start()
    time.sleep(1.5)  # let the bomb take every process slot it can
    victim = run_jailed(["/usr/local/bin/python3", "-I", "/work/needs_forks.py"],
                        jobs["needs_forks.py"], limits)
    bomb.join()
    print("concurrency: bomb ->", results["bomb"].stdout.strip(),
          "| victim ->", victim.stdout.strip() or victim.stderr.strip()[-200:])
    return "children ok" in victim.stdout


if __name__ == "__main__" and os.environ.get("SPIKE_CONCURRENCY"):
    sys.exit(0 if concurrency_check() else 1)
