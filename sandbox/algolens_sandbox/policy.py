"""Seccomp policy for code inside the jail (kafel syntax), applied by nsjail.

The container's seccomp profile has to allow namespace syscalls so nsjail can build the jail.
This policy takes them away again from the jailed program, along with other kernel attack
surface that solution code never needs. See sandbox/spike/RESULTS.md.

kafel's amd64 table predates some syscalls, so those use raw x86-64 numbers:
425-427 = io_uring_setup/enter/register; 435 = clone3, which gets ENOSYS so glibc falls back
to clone (filtered below). kafel spells umount2 "umount".
"""

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
