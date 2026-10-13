# M1 nsjail spike: results

**Verdict: pass.** nsjail isolates untrusted Python and C++ inside an unprivileged container, started with `docker compose`, on this machine (Windows 11, WSL2 kernel 6.6, Docker Engine 29.9 inside Ubuntu 24.04). There's no `privileged`, no `CAP_SYS_ADMIN`, and in fact no capabilities at all (`cap_drop: [ALL]`). The only relaxation is a custom seccomp profile (below).

Run it with:

```sh
cd sandbox/spike
python3 make_seccomp.py                           # regenerates seccomp-nsjail.json
docker compose up -d canary
docker compose run --rm --build spike             # 13 containment cases
docker compose run --rm -e SPIKE_CONCURRENCY=1 spike   # cross-job starvation check
docker compose down
```

## Results (2026-10-13)

| Case | Expected | Got | Evidence |
|---|---|---|---|
| Python runs | ok | ok | `hello from python 3.12.15` |
| C++ compiles (in jail) and runs | ok | ok | `hello from c++ 123` |
| Network | blocked | blocked | 1.1.1.1, 8.8.8.8, `db`, `host.docker.internal` all fail |
| Host files | hidden | hidden | jail root is only `bin etc lib lib64 tmp usr work`; `/etc/passwd`, runner source, `/proc`, docker socket absent; `/usr` and `/work` read-only |
| CPU limit (2 s) | timeout | timeout | killed at 2.01 s CPU |
| Wall-time limit (3 s) | timeout | timeout | killed at 3.0 s while sleeping |
| Python memory (256 MB) | memory | memory | `MemoryError` |
| C++ memory (256 MB) | memory | memory | `std::bad_alloc` |
| Fork bomb | contained | contained | fork fails after 15 children (`EAGAIN`) |
| Output flood | output_limit | output_limit | runner kills at 1 MiB |
| Disk fill | contained | contained | stops at 16 MB (`/tmp` tmpfs size, `RLIMIT_FSIZE`) |
| C++ null deref | runtime_error | runtime_error | SIGSEGV (exit 139) |
| Privilege escape | blocked | blocked | `mount`, `unshare(user/net)`, `setns`, `chroot`, `setuid(0)` all `EPERM`; `kill(-1)` finds nothing to kill |
| Neighbour container | unaffected | unaffected | canary heartbeat max gap 0.213 s (normal 0.2 s) during the whole run |
| Concurrent job vs fork bomb | unaffected | unaffected | victim's 4 subprocesses all succeed while the bomb holds 15 |

## Security layers, and why each is there

1. **Container** (`compose.yml`): no network, read-only root filesystem, every capability dropped, `no-new-privileges`, memory 1 GB, 256 pids, 2 CPUs. `/tmp` is `noexec`; job folders get their own `exec` tmpfs (`/jobs`) so compiled C++ can run.
2. **Container seccomp** (`seccomp-nsjail.json`): Docker's default profile with exactly one change, so that nsjail can build its jail without `CAP_SYS_ADMIN`:
   - *removed*: Docker's two argument-filtered `clone` rules (they forbid namespace flags without `CAP_SYS_ADMIN`)
   - *added*: allow `clone`, `unshare`, `setns`, `mount`, `umount2`, `pivot_root`, `sethostname`
3. **nsjail**: fresh user/mount/PID/net/IPC/UTS/cgroup namespaces per run, an empty root with read-only toolchain mounts, an unprivileged uid, and rlimits for CPU, address space, file size, process count, open files and stack, plus a wall-time limit.
4. **Seccomp for the jailed program** (kafel policy in `run_spike.py`): **takes back** what layer 2 allowed, plus other kernel attack surface. It blocks `unshare`, `setns`, `mount`, `umount`, `pivot_root`, `chroot`, `ptrace`, `bpf`, `perf_event_open`, `userfaultfd`, `io_uring_*`, keyring calls, module loading, `kexec`, `process_vm_*`, handle-based opens, and `clone` with any namespace flag. `clone3` returns ENOSYS, so glibc falls back to `clone`.
5. **Runner**: caps stdout at 1 MiB, has a watchdog beyond nsjail's own time limit, and measures CPU time via `wait4`.

## Things the spike taught us (carried into the real M1 build)

- **A launch failure must never look like the program's failure.** In the first run, the "C++ segfault" case *passed* even though the binary never executed. Rule: if nsjail's log doesn't show that it started the program, the outcome is `sandbox_error`, never a verdict about the code. A `sandbox_error` must never count toward or against verification.
- **Jailed code could create user namespaces** until layer 4 was added. That layer is mandatory, not optional.
- **The CPU limit kills with SIGKILL**, because nsjail sets soft = hard. A CPU timeout is identified by the CPU time `wait4` reports, not by the signal.
- **There are no cgroups inside the container**: `/sys/fs/cgroup` is read-only without privileged mode. Memory is limited by `RLIMIT_AS` (virtual memory) and processes by `RLIMIT_NPROC`, with the container's own cgroup limits as the backstop. The process limit is counted per user namespace on this kernel, so jobs don't starve each other. The container's 256-pid cap therefore bounds concurrency at about 12 jobs per sandbox container at 16 processes each.
- **Memory classification for C++** relies on `bad_alloc` reaching stderr. The real harness will catch `std::bad_alloc` itself and report it explicitly.
- **kafel's syscall table is older than the kernel**: `umount2` is spelled `umount`, and `io_uring_*`/`clone3` need raw numbers (425–427, 435).

## Open risk for CI and other Linux hosts

This machine's WSL kernel has no AppArmor. GitHub's `ubuntu-24.04` runners (and stock Ubuntu hosts) do, and two things there may block nsjail:
- Docker's `docker-default` AppArmor profile denies `mount`
- `kernel.apparmor_restrict_unprivileged_userns=1` restricts unprivileged user namespaces

Expect to need `apparmor=unconfined` (or a small custom AppArmor profile) on the sandbox service, and possibly the sysctl changed on the CI runner. This will come up in M1 when the sandbox joins the main compose file and the CI compose job runs it.
