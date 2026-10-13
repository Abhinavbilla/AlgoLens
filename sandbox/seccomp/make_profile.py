"""Build sandbox.json from Docker's default profile.

The only change: allow the namespace/mount syscalls nsjail needs to build its jail, without
granting CAP_SYS_ADMIN to the container. Everything else stays exactly as Docker's default.
nsjail then applies its own, much tighter limits to the code it runs.

Source profile: https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
NSJAIL_SYSCALLS = ["clone", "unshare", "setns", "mount", "umount2", "pivot_root", "sethostname"]


def build(default: dict) -> dict:
    profile = json.loads(json.dumps(default))
    rules = []
    for rule in profile["syscalls"]:
        # Drop Docker's argument-filtered clone rules (they forbid namespace flags without
        # CAP_SYS_ADMIN); the unconditional rule below replaces them.
        if rule["names"] == ["clone"] and rule.get("args"):
            continue
        rules.append(rule)
    rules.append(
        {
            "names": NSJAIL_SYSCALLS,
            "action": "SCMP_ACT_ALLOW",
            "comment": "AlgoLens: let nsjail create namespaces without CAP_SYS_ADMIN",
        }
    )
    profile["syscalls"] = rules
    return profile


if __name__ == "__main__":
    default = json.loads((HERE / "docker-default.json").read_text())
    out = build(default)
    (HERE / "sandbox.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"rules: {len(default['syscalls'])} -> {len(out['syscalls'])}")
