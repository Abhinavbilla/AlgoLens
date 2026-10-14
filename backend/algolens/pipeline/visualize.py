"""Animations for generated approaches (plan §7, M6).

For each verified approach the narration model proposes a visual spec, narration templates
and a Python-to-C++ line map. They are compiled and linted against real recordings of the
worked examples, exactly as library entries are. If the proposal doesn't compile or lint
clean, the model gets one more try with the errors; after that, templates that still cause
lint errors are dropped (their lines get the neutral sentence), and a visual spec that still
fails is replaced by a generic one derived from the recorded variables. So an animation is
never wrong, only plainer.
"""

import logging
import re
from typing import Any

from pydantic import BaseModel

from algolens.ai.budget import BudgetExhausted
from algolens.animation.builder import AnimationError, before_view, build, compile_visual
from algolens.animation.values import FrameView
from algolens.narration.engine import TemplateError, compile_templates, lint
from algolens.pipeline import prompts
from algolens.sandbox.client import SandboxClient, SandboxUnavailable

log = logging.getLogger("algolens.pipeline")
MAX_EXAMPLES = 4  # recordings used for linting
MAX_GENERIC_PANELS = 5


class VisualPlan(BaseModel):
    visual: dict
    narration: list[dict] = []
    cpp_lines: dict[str, int] = {}


class Recording:
    def __init__(self, args: list, trace: dict):
        self.args = args
        self.trace = trace
        self.views = [FrameView(f, trace["heap"]) for f in trace["frames"]]
        self.befores = [
            before_view(self.views[i - 1] if i else None, v) for i, v in enumerate(self.views)
        ]


class AnimationSource:
    """What the animation service needs (duck-typed like library EntrySource)."""

    def __init__(self, approach_id: str, entry: str, python_code: str, extras: dict,
                 plan: dict):  # fmt: skip
        self.entry = entry
        self.python_code = python_code
        self._extras = extras
        self.visual = plan["visual"]
        self.narration = plan["narration"]
        self.cpp_lines = plan.get("cpp_lines", {})
        self.default_input = plan["default_input"]
        self.content_hash = f"approach:{approach_id}:{plan.get('version', 1)}"

    def sandbox_extras(self) -> dict:
        return dict(self._extras)

    def cpp_line_map(self) -> dict[int, int]:
        return {int(k): v for k, v in self.cpp_lines.items()}


def sandbox_extras(spec: dict) -> dict:
    kinds = [p.get("type", {}).get("kind") for p in spec.get("params", [])]
    convert = [k if k in ("binary_tree", "linked_list") else None for k in kinds]
    extras: dict[str, Any] = {"convert": convert} if any(convert) else {}
    if spec.get("result_kind"):
        extras["convert_result"] = spec["result_kind"]
    return extras


def record(
    sandbox: SandboxClient, spec: dict, code: str, args: list
) -> tuple[Recording | None, str]:
    resp = sandbox.trace({"source": code, "entry": spec["function_name"], "input": {"args": args},
                          **sandbox_extras(spec)})  # fmt: skip
    if resp["status"] == "sandbox_error":
        raise SandboxUnavailable(resp.get("detail", "sandbox error while recording"))
    if resp["status"] != "ok":
        return None, f"{resp['status']}: {resp.get('detail', '')}".strip(": ")
    rec = Recording(args, resp["trace"])
    if resp["trace"].get("truncated") or len(rec.views) > 300:
        return None, "too many steps to animate"
    return rec, ""


def plan_animation(run, spec: dict, python_code: str, cpp_code: str) -> dict:
    """{"visual", "narration", "cpp_lines", "default_input", "source", "lint"} or
    {"unavailable": reason}. `run` provides ask() and sandbox (pipeline.solve._Run)."""
    recordings, why = [], ""
    for ex in spec.get("examples", [])[:MAX_EXAMPLES]:
        rec, problem = record(run.sandbox, spec, python_code, ex["args"])
        if rec:
            recordings.append(rec)
        else:
            why = why or problem
    if not recordings:
        return {"unavailable": f"The worked examples couldn't be animated ({why})."}
    default = min(recordings, key=lambda r: len(r.views))
    n_py, n_cpp = len(python_code.splitlines()), len(cpp_code.splitlines())

    problem, plan, attempts = "", None, []
    for _ in range(2):
        try:
            proposal = run.ask("narration", prompts.VISUAL_SYSTEM,
                               prompts.visual_prompt(spec, python_code, cpp_code, problem),
                               VisualPlan)  # fmt: skip
        except BudgetExhausted:
            raise
        except Exception as exc:  # a bad reply: fall back below, never fail the problem
            log.warning("visual plan reply unusable: %s", exc)
            break
        plan, errors = _check(proposal, recordings, default, python_code, n_py, n_cpp)
        attempts.append(errors[:15])
        if not errors:
            plan["lint"]["retried"] = bool(problem)
            break
        problem = "\n".join(errors[:15])
    if plan is None:
        plan = {"visual": generic_visual(default, python_code), "narration": [], "cpp_lines": {},
                "source": "generic", "lint": {"errors": [], "dropped": []}}  # fmt: skip
    else:
        plan = _salvage(plan, recordings, default, python_code)
    plan["default_input"] = {"args": default.args}
    plan.setdefault("lint", {})["attempts"] = attempts  # lint errors of each AI proposal
    return plan


def _check(p: VisualPlan, recs: list[Recording], default: Recording, code: str, n_py: int,
           n_cpp: int) -> tuple[dict, list[str]]:  # fmt: skip
    errors: list[str] = []
    cpp_lines = {}
    for k, v in p.cpp_lines.items():
        if str(k).isdigit() and 1 <= int(k) <= n_py and isinstance(v, int) and 1 <= v <= n_cpp:
            cpp_lines[str(int(k))] = v  # bad pairs are dropped, not fatal
    plan = {"visual": p.visual, "narration": p.narration, "cpp_lines": cpp_lines, "source": "ai",
            "lint": {"errors": [], "dropped": []}}  # fmt: skip
    plan["visual"] = unwrap_braces(p.visual)
    try:
        panels = compile_visual(plan["visual"])
    except AnimationError as exc:
        return plan, [f"visual: {exc}"]
    try:
        templates = compile_templates(p.narration)
    except TemplateError as exc:
        return plan, [f"narration: {exc}"]
    errors += [f"template {t.index} refers to line {t.line}, but the code has {n_py} lines"
               for t in templates if not 1 <= t.line <= n_py]  # fmt: skip
    try:
        build(default.trace, source=code, templates=templates, panels=panels)
    except AnimationError as exc:
        errors.append(f"visual: {exc}")
    except Exception as exc:  # a panel that can't draw this data
        errors.append(f"visual: a panel failed on the recording ({type(exc).__name__}: {exc})")
    views = [v for r in recs for v in r.views]
    befores = [b for r in recs for b in r.befores]
    errors += [f"narration: {e}" for e in lint(templates, views, befores)["errors"]]
    return plan, errors


def _salvage(plan: dict, recs: list[Recording], default: Recording, code: str) -> dict:
    """Make a plan that still has errors safe: generic visual if the panels fail, and drop
    the templates lint keeps complaining about."""
    try:
        panels = compile_visual(plan["visual"])
        build(default.trace, source=code, templates=[], panels=panels)
    except Exception:
        plan["visual"], plan["source"] = generic_visual(default, code), "ai+generic visual"
    try:
        templates = compile_templates(plan["narration"])
    except TemplateError:
        plan["lint"]["dropped"] = list(range(len(plan["narration"])))
        plan["narration"] = []
        return plan
    n_py = len(code.splitlines())
    keep = [t for t in templates if 1 <= t.line <= n_py]
    views = [v for r in recs for v in r.views]
    befores = [b for r in recs for b in r.befores]
    for _ in range(len(keep) + 1):
        errors = lint(keep, views, befores)["errors"] if keep else []
        if not errors:
            break
        bad = culprits(errors) & {t.index for t in keep}
        keep = [t for t in keep if t.index not in bad] if bad else []
    kept = {t.index for t in keep}
    plan["lint"]["dropped"] = [i for i in range(len(plan["narration"])) if i not in kept]
    plan["narration"] = [t for i, t in enumerate(plan["narration"]) if i in kept]
    if plan["lint"]["dropped"]:
        plan["source"] += " (some narration dropped)"
    return plan


def unwrap_braces(v: Any) -> Any:
    """Models often write panel expressions like narration placeholders ("{nums}"); panel
    fields are bare expressions, so strip one pair of enclosing braces. Nothing else changes:
    the result is still compiled and checked like any visual spec."""
    if isinstance(v, dict):
        return {k: unwrap_braces(x) for k, x in v.items()}
    if isinstance(v, list):
        return [unwrap_braces(x) for x in v]
    if isinstance(v, str):
        t = v.strip()
        if t.startswith("{") and t.endswith("}") and t.count("{") == 1 and t.count("}") == 1:
            return t[1:-1].strip()
    return v


def culprits(errors: list[str]) -> set[int]:
    """Templates to drop for these lint errors: ungrounded ones, and for overlapping
    templates that disagree, every one but the first (which is the one that's shown)."""
    out: set[int] = set()
    for e in errors:
        m = re.match(r"template (\d+) at line", e)
        if m:
            out.add(int(m.group(1)))
        m = re.search(r"templates \[([\d, ]+)\]", e)
        if m:
            out.update(sorted(int(x) for x in m.group(1).split(","))[1:])
    return out


def generic_visual(rec: Recording, code: str) -> dict:
    """Panels for whatever the recording holds: arrays, maps, trees and linked lists by
    shape, everything scalar in one variables panel. Verified to build on `rec`."""
    names: list[str] = []
    for view in rec.views:
        for name in view.own()["locals"]:
            if name not in names:
                names.append(name)
    shapes: dict[str, str] = {}
    for name in names:
        for view in reversed(rec.views):
            try:
                value = view.plain(view.lookup(name))
            except KeyError:
                continue
            shapes[name] = _shape(value)
            break
    panels: list[dict] = []
    for name in names:
        kind = shapes.get(name)
        if kind in ("array", "map", "tree", "linked_list") and len(panels) < MAX_GENERIC_PANELS - 1:
            panels.append({"kind": kind, "var": name})
    scalars = [n for n in names if shapes.get(n) == "scalar"][:10]
    if scalars:
        panels.append({"kind": "vars", "vars": scalars})
    # Keep only panels that draw on the recording.
    good = []
    for p in panels:
        try:
            build(rec.trace, source=code, templates=[], panels=compile_visual({"panels": [p]}))
            good.append(p)
        except Exception:
            continue
    return {"panels": good}


def _shape(v: Any) -> str:
    scalar = (bool, int, float, str, type(None))
    if isinstance(v, scalar):
        return "scalar"
    if isinstance(v, list) and all(isinstance(x, scalar) for x in v):
        return "array"
    if isinstance(v, dict):
        if set(v) >= {"val", "left", "right"}:
            return "tree"
        if set(v) >= {"val", "next"}:
            return "linked_list"
        if all(isinstance(x, scalar) for x in v.values()):
            return "map"
    return "other"
