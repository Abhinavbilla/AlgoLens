"""Record a run in the sandbox and build its animation."""

import json
import threading
from collections import OrderedDict

from algolens.animation.builder import AnimationError, build, compile_visual
from algolens.library.loader import EntrySource
from algolens.narration.engine import compile_templates
from algolens.sandbox.client import SandboxClient

CACHE_SIZE = 256


class TraceFailed(Exception):
    """The sandbox couldn't produce a faithful recording for this input."""

    def __init__(self, status: str, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def animate(entry: EntrySource, args_input: dict, client: SandboxClient) -> dict:
    resp = client.trace({"source": entry.python_code, "entry": entry.entry, "input": args_input,
                         **entry.sandbox_extras()})  # fmt: skip
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


# Recordings are deterministic, so animations are cached per (entry version, input): replays
# are instant and keep working if the sandbox restarts.
_cache: OrderedDict[str, dict] = OrderedDict()
_lock = threading.Lock()


def cached_animation(entry: EntrySource, args_input: dict) -> dict:
    key = entry.content_hash + json.dumps(args_input, sort_keys=True)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    client = SandboxClient()
    try:
        animation = animate(entry, args_input, client)
    finally:
        client.close()
    with _lock:
        _cache[key] = animation
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return animation


def default_animation(entry: EntrySource) -> dict:
    return cached_animation(entry, entry.default_input)


__all__ = ["AnimationError", "TraceFailed", "animate", "cached_animation", "default_animation"]
