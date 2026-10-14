"""Record a run in the sandbox and build its animation."""

import threading

from algolens.animation.builder import AnimationError, build, compile_visual
from algolens.library.loader import EntrySource
from algolens.narration.engine import compile_templates
from algolens.sandbox.client import SandboxClient


class TraceFailed(Exception):
    """The sandbox couldn't produce a faithful recording for this input."""

    def __init__(self, status: str, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def animate(entry: EntrySource, args_input: dict, client: SandboxClient) -> dict:
    resp = client.trace({"source": entry.python_code, "entry": entry.entry, "input": args_input})
    if resp["status"] != "ok":
        raise TraceFailed(resp["status"], resp.get("detail", ""))
    animation = build(
        resp["trace"],
        source=entry.python_code,
        templates=compile_templates(entry.narration),
        panels=compile_visual(entry.visual),
        cpp_lines=entry.cpp_line_map(),
    )
    animation["result"] = resp["value"]
    animation["input"] = args_input
    return animation


_cache: dict[str, dict] = {}
_lock = threading.Lock()


def default_animation(entry: EntrySource) -> dict:
    """Recordings are deterministic, so the default input's animation is cached per entry
    version: replays are instant and keep working if the sandbox restarts."""
    key = entry.content_hash
    with _lock:
        if key in _cache:
            return _cache[key]
    client = SandboxClient()
    try:
        animation = animate(entry, entry.default_input, client)
    finally:
        client.close()
    with _lock:
        _cache[key] = animation
    return animation


__all__ = ["AnimationError", "TraceFailed", "animate", "default_animation"]
