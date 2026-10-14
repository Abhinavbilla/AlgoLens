"""Turn a recorded trace into what the player shows (plan §7.3).

Every frame of the output corresponds to exactly one recorded frame, in order; nothing is
interpolated. Panels (animation/panels.py) are resolved here from that frame's state, so the
browser only draws them. A visual spec chooses what to show and how, never values.
"""

from typing import Any

from algolens.animation.panels import Panel, VisualError, render
from algolens.animation.panels import compile_visual as _compile_panels
from algolens.animation.values import FrameView, display
from algolens.narration.engine import NarrationTemplate, narrate

MAX_FRAMES = 300  # spec: an animation has at most 300 frames


class AnimationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # "too_long" (caller should pick a smaller input) or "bad_visual"


def compile_visual(spec: dict) -> list[Panel]:
    try:
        return _compile_panels(spec)
    except VisualError as exc:
        raise AnimationError("bad_visual", str(exc)) from exc


# --- building ----------------------------------------------------------------------------------


def build(
    trace: dict,
    *,
    source: str,
    templates: list[NarrationTemplate],
    panels: list[Panel],
    cpp_lines: dict[int, int] | None = None,
) -> dict:
    if trace.get("truncated"):
        raise AnimationError("too_long", f"recording stopped early ({trace['truncated']})")
    frames, heap = trace["frames"], trace["heap"]
    if len(frames) > MAX_FRAMES:
        raise AnimationError("too_long", f"{len(frames)} steps; the limit is {MAX_FRAMES}")
    lines = source.splitlines()
    views = [FrameView(f, heap) for f in frames]
    out = []
    for i, view in enumerate(views):
        before = before_view(views[i - 1] if i else None, view)
        f = view.frame
        frame: dict[str, Any] = {
            "i": i,
            "line": f["line"],
            "next": f["next"],
            "cpp_line": nearest_cpp_line(cpp_lines or {}, f["line"]),
            "code": lines[f["line"] - 1].strip() if 0 < f["line"] <= len(lines) else "",
            "ops": i + 1,
            "aid": f["aid"],
            "stack": [_stack_entry(a, view, before) for a in f["stack"]],
            "panels": [render(p, view, before) for p in panels],
            "narration": narrate(templates, view, before),
        }
        if "ret" in f:
            frame["ret"] = display(view.plain(f["ret"]))
        if "raised" in f:
            frame["raised"] = f["raised"]
        out.append(frame)
    return {"frames": out, "total_ops": len(out)}


def before_view(prev: FrameView | None, cur: FrameView) -> FrameView | None:
    """The state just before `cur`'s line ran, seen from `cur`'s activation. None if that
    activation didn't exist yet (its first line), so nothing is marked as changed."""
    if prev is None or not prev.has_activation(cur.frame["aid"]):
        return None
    return FrameView(prev.frame, prev.heap, aid=cur.frame["aid"])


def nearest_cpp_line(mapping: dict[int, int], py_line: int) -> int | None:
    """The mapped C++ line, or that of the closest earlier mapped Python line."""
    if py_line in mapping:
        return mapping[py_line]
    earlier = [p for p in mapping if p < py_line]
    return mapping[max(earlier)] if earlier else None


def _stack_entry(act: dict, view: FrameView, before: FrameView | None) -> dict:
    args = ", ".join(
        f"{p}={display(view.plain(act['locals'][p]))}" for p in act.get("params", [])
        if p in act["locals"]
    )  # fmt: skip
    call = f"{act['fn']}({args})"
    return {
        "aid": act["aid"],
        "fn": act["fn"],
        "line": act["line"],
        "call": call if len(call) <= 80 else call[:79] + "…",
        "new": before is None or not before.has_activation(act["aid"]),
    }
