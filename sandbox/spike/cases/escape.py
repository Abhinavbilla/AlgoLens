# Privileged operations must fail even though the jail runs as "root" in its own namespace view.
import ctypes, os, signal
libc = ctypes.CDLL(None, use_errno=True)
def check(name, rc):
    print(("ALLOWED " if rc == 0 else "blocked ") + name, ctypes.get_errno() if rc != 0 else "")
check("mount tmpfs on /usr", libc.mount(b"none", b"/usr", b"tmpfs", 0, None))
check("unshare user ns", libc.unshare(0x10000000))
check("unshare net ns", libc.unshare(0x40000000))
check("setns", libc.setns(0, 0))
check("chroot /", libc.chroot(b"/"))
try:
    os.setuid(0); print("ALLOWED setuid 0", os.getuid())
except OSError as e:
    print("blocked setuid 0", type(e).__name__)
# kill(-1) may only reach processes inside the jail's own PID namespace.
try:
    os.kill(-1, signal.SIGKILL)  # never signals the caller itself
    print("kill -1 sent")
except ProcessLookupError:
    print("kill -1 found nothing to kill")
print("still here after kill -1")
