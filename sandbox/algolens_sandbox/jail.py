"""Build and run nsjail invocations. Runs in the sandbox container, never inside a jail."""

import contextlib
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from algolens_sandbox.policy import CHILD_SECCOMP

NSJAIL = "/usr/local/bin/nsjail"
DRIVER_DIR = "/opt/algolens/driver"
TOOLCHAIN_MOUNTS = ["/usr", "/lib", "/lib64", "/bin", "/etc/ld.so.cache"]
STDERR_CAP = 64 << 10
JAIL_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "PYTHONHASHSEED": "0",  # set/dict iteration order must be reproducible across runs
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}


@dataclass(frozen=True)
class JailLimits:
    wall_s: int
    cpu_s: int
    mem_mb: int
    nproc: int = 16
    fsize_mb: int = 16
    tmp_mb: int = 16


@dataclass
class JailRun:
    exit_code: int
    wall_s: float
    cpu_s: float
    stdout: bytes
    stderr: bytes
    log: str
    stdout_capped: bool
    hit_time_limit: bool = False  # our monotonic watchdog stopped it at limits.wall_s

    @property
    def started(self) -> bool:
        """Whether nsjail actually started the program. If not, nothing it reports is a
        verdict on the code: callers must treat it as a sandbox error."""
        return "Executing '" in self.log and "Launching child process failed" not in self.log


def command(
    argv: list[str], work: Path, limits: JailLimits, writable_work: bool, log: Path
) -> list[str]:
    cmd = [NSJAIL, "--mode", "o", "--log", str(log)]
    for mount in TOOLCHAIN_MOUNTS:  # on an otherwise empty tmpfs root
        cmd += ["-R", mount]
    cmd += ["-R", f"{DRIVER_DIR}:/driver"]
    cmd += ["-B" if writable_work else "-R", f"{work}:/work"]
    cmd += ["-m", f"none:/tmp:tmpfs:size={limits.tmp_mb << 20}"]
    cmd += ["--cwd", "/work", "--hostname", "jail", "--disable_proc"]
    cmd += ["--user", "99999", "--group", "99999"]
    cmd += [
        "--time_limit", "0",  # disabled: see run(); we enforce wall time on a monotonic clock
        "--rlimit_cpu", str(limits.cpu_s),
        "--rlimit_as", str(limits.mem_mb),
        "--rlimit_fsize", str(limits.fsize_mb),
        "--rlimit_nproc", str(limits.nproc),
        "--rlimit_nofile", "64",
        "--rlimit_stack", "64",
        # 1 MB hard limit so the driver can lower it to the 1-byte "no core dumps" value.
        "--rlimit_core", "1",
    ]  # fmt: skip
    for key, value in JAIL_ENV.items():
        cmd += ["--env", f"{key}={value}"]
    cmd += ["--seccomp_string", CHILD_SECCOMP, "--", *argv]
    return cmd


def _kill_group(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


def run(
    argv: list[str],
    work: Path,
    limits: JailLimits,
    *,
    writable_work: bool = False,
    stdout_cap: int = 1 << 20,
) -> JailRun:
    log = work.parent / f"nsjail-{time.monotonic_ns()}.log"
    cmd = command(argv, work, limits, writable_work, log)
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    # The wall-time limit is enforced here on a monotonic clock, not by nsjail: nsjail 3.4
    # measures it with the wall clock, and when the host clock steps backwards (WSL does
    # this when it resyncs) it computes a negative run time and kills healthy jobs at once.
    # Killing nsjail's process group also kills the jailed program: it shares the group, and
    # when the jail's PID 1 dies the kernel ends everything else in that PID namespace.
    timed_out = threading.Event()

    def on_timeout() -> None:
        timed_out.set()
        _kill_group(proc.pid)

    watchdog = threading.Timer(limits.wall_s, on_timeout)
    watchdog.start()
    stderr = bytearray()

    def drain_stderr() -> None:
        # Keep reading past the cap so a chatty program can never block on a full pipe.
        while chunk := proc.stderr.read1(65536):
            if len(stderr) < STDERR_CAP:
                stderr.extend(chunk[: STDERR_CAP - len(stderr)])

    reader = threading.Thread(target=drain_stderr, daemon=True)
    reader.start()
    out, capped = bytearray(), False
    while chunk := proc.stdout.read1(65536):
        out += chunk
        if len(out) > stdout_cap:
            capped = True
            _kill_group(proc.pid)
            break
    # wait4 gives CPU time including the jailed program, which nsjail reaps.
    _, status, usage = os.wait4(proc.pid, 0)
    proc.returncode = os.waitstatus_to_exitcode(status)
    watchdog.cancel()
    reader.join(timeout=5)
    return JailRun(
        exit_code=proc.returncode,
        wall_s=round(time.monotonic() - start, 3),
        cpu_s=round(usage.ru_utime + usage.ru_stime, 3),
        stdout=bytes(out[:stdout_cap]),
        stderr=bytes(stderr),
        log=log.read_text(errors="replace") if log.exists() else "",
        stdout_capped=capped,
        hit_time_limit=timed_out.is_set(),
    )
