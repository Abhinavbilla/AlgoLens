# An innocent program that needs a few processes.
import subprocess
outs = [subprocess.run(["/usr/local/bin/python3", "-c", "print(1)"], capture_output=True).returncode
        for _ in range(4)]
print("children ok" if outs == [0, 0, 0, 0] else f"children failed {outs}")
