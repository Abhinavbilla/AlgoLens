# The jail must not see the container's files, only the read-only toolchain mounts.
import os
print("root:", sorted(os.listdir("/")))
for path in ["/etc/passwd", "/etc/hostname", "/spike/run_spike.py", "/proc/1/environ",
             "/proc/self/mounts", "/home/runner", "/var/run/docker.sock"]:
    try:
        with open(path) as f:
            f.read(1)
        print("READABLE", path)
    except OSError as e:
        print("blocked", path, type(e).__name__)
for path in ["/usr/evil", "/work/evil"]:
    try:
        open(path, "w").write("x")
        print("WRITABLE", path)
    except OSError as e:
        print("blocked", path, type(e).__name__)
