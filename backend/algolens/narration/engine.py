"""Choose and render one sentence of narration per frame (plan §7.4).

A template applies to a frame when its `line` is the line that just ran, its `next` (if
given) is the line that runs next (so it knows which branch was taken), and its `when`
condition is True on that frame's values. The first applicable template in declared order
wins. If none applies, or rendering fails, or the sentence would contain a number that
didn't come from the state, a neutral sentence built from the actual changes is used.

Rendering: a state path shows its value; a computed value always shows its operands
("2 + 15 = 17"). A top-level len() shows just its value, since its operand is a container
that's already on screen.
"""

import re
from dataclasses import dataclass
from typing import Any

from algolens.animation.values import FrameView, display, numbers_in
from algolens.narration import expr
from algolens.narration.expr import BinOp, ExprError, Len, Neg, Node, evaluate
from algolens.narration.template import (
    Placeholder,
    Template,
    is_small_literal,
    parse_condition,
    parse_template,
)

ANY = object()  # template applies whatever line runs next
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_SYMBOL = {"+": "+", "-": "-", "*": "×", "//": "//", "%": "mod"}
_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "//": 2, "%": 2}


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class NarrationTemplate:
    index: int
    line: int
    next: Any  # int, "return", or ANY
    when: Node | None
    text: Template
    raw_text: str


def compile_templates(raw: list[dict]) -> list[NarrationTemplate]:
    out = []
    for i, t in enumerate(raw):
        where = f"template {i}"
        if not isinstance(t, dict) or set(t) - {"line", "next", "when", "text"}:
            raise TemplateError(f"{where}: unexpected keys")
        if not isinstance(t.get("line"), int) or isinstance(t.get("line"), bool):
            raise TemplateError(f"{where}: `line` must be an integer")
        nxt = t.get("next", ANY)
        if nxt is not ANY and nxt != "return" and not (isinstance(nxt, int) and nxt > 0):
            raise TemplateError(f'{where}: `next` must be a line number or "return"')
        try:
            when = parse_condition(t["when"]) if "when" in t else None
            text = parse_template(t["text"])
        except ExprError as exc:
            raise TemplateError(f"{where}: {exc}") from exc
        out.append(NarrationTemplate(i, t["line"], nxt, when, text, t["text"]))
    return out


def applicable(t: NarrationTemplate, view: FrameView, before: FrameView | None) -> bool:
    frame = view.frame
    if t.line != frame["line"]:
        return False
    if t.next is not ANY and t.next != frame["next"]:
        return False
    if t.when is None:
        return True
    try:
        return evaluate(t.when, view.env(before)) is True  # a real bool, not just truthy
    except ExprError:
        return False


def narrate(templates: list[NarrationTemplate], view: FrameView, before: FrameView | None) -> dict:
    for t in templates:
        if not applicable(t, view, before):
            continue
        try:
            text, produced = render(t.text, view, before)
        except ExprError:
            continue
        if ungrounded_numbers(text, view, produced):
            continue
        return {"text": text, "source": "template", "template": t.index}
    return neutral(view, before)


def render(template: Template, view: FrameView, before: FrameView | None) -> tuple[str, set[str]]:
    env = view.env(before)
    produced: set[str] = set()
    parts = []
    for seg in template.segments:
        if isinstance(seg, Placeholder):
            parts.append(_render_placeholder(seg, view, env, produced))
        else:
            parts.append(seg)
    return "".join(parts), produced


def _render_placeholder(p: Placeholder, view: FrameView, env, produced: set[str]) -> str:
    if not p.computed:
        value = view.plain(evaluate(p.node, env))
        numbers_in(value, produced)
        return display(value)
    if isinstance(p.node, Len):
        value = evaluate(p.node, env)
        produced.add(display(value))
        return display(value)
    text, value = _render_computed(p.node, view, env, produced)
    produced.add(display(value))
    return f"{text} = {display(value)}"


def _render_computed(node: Node, view: FrameView, env, produced: set[str]) -> tuple[str, Any]:
    if expr.is_path(node) or isinstance(node, Len):
        value = view.plain(evaluate(node, env))
        numbers_in(value, produced)
        return display(value), value
    if is_small_literal(node):  # a constant operand, shown as part of the working
        value = evaluate(node, env)
        produced.add(display(value))
        return display(value), value
    if isinstance(node, Neg):
        text, _ = _render_computed(node.operand, view, env, produced)
        wrap = isinstance(node.operand, BinOp)
        value = evaluate(node, env)
        produced.add(display(value))
        return (f"-({text})" if wrap else f"-{text}"), value
    if isinstance(node, BinOp):
        left, _ = _render_computed(node.left, view, env, produced)
        right, _ = _render_computed(node.right, view, env, produced)
        if isinstance(node.left, BinOp) and _PRECEDENCE[node.left.op] < _PRECEDENCE[node.op]:
            left = f"({left})"
        if isinstance(node.right, BinOp) and _PRECEDENCE[node.right.op] <= _PRECEDENCE[node.op]:
            right = f"({right})"
        return f"{left} {_SYMBOL[node.op]} {right}", evaluate(node, env)
    raise ExprError(f"cannot render {type(node).__name__}")


def state_numbers(view: FrameView) -> set[str]:
    out: set[str] = set()
    for act in view.activations():
        for v in act["locals"].values():
            numbers_in(view.plain(v), out)
    if "ret" in view.frame:
        numbers_in(view.plain(view.frame["ret"]), out)
    return out


def ungrounded_numbers(text: str, view: FrameView, produced: set[str]) -> list[str]:
    """Numbers in `text` that neither appear in the frame's state nor were computed by the
    engine from it (the final guard: a template can never introduce a number)."""
    allowed = state_numbers(view) | produced
    return [m for m in _NUMBER.findall(text) if m not in allowed]


def neutral(view: FrameView, before: FrameView | None) -> dict:
    """True by construction: describes only what the recording shows changed."""
    frame = view.frame
    parts = []
    if "raised" in frame:
        parts.append(f"raised {frame['raised']}")
    elif frame["next"] == "return" and "ret" in frame:
        parts.append(f"returned {display(view.plain(frame['ret']))}")
    own = view.own()
    prev = _same_activation_locals(before, frame["aid"])
    changes = []
    for name, enc in own["locals"].items():
        new = view.plain(enc)
        if prev is None:
            continue
        if name not in prev:
            changes.append(f"{name} = {display(new)}")
            continue
        old = before.plain(prev[name])
        if old == new:
            continue
        if _scalar(old) and _scalar(new):
            changes.append(f"{name} changed from {display(old)} to {display(new)}")
        else:
            changes.append(f"{name} changed")
    if len(changes) > 3:
        changes = changes[:3] + [f"{len(changes) - 3} more changed"]
    parts += changes
    text = "; ".join(parts) if parts else "nothing changed"
    return {"text": text[0].upper() + text[1:], "source": "neutral"}


def _same_activation_locals(before: FrameView | None, aid: int) -> dict | None:
    if before is None:
        return None
    for act in before.activations():
        if act["aid"] == aid:
            return act["locals"]
    return None


def _scalar(v: Any) -> bool:
    return v is None or isinstance(v, bool | int | float | str)


def lint(templates: list[NarrationTemplate], views: list[FrameView],
         befores: list[FrameView | None]) -> dict:  # fmt: skip
    """Run every template against recorded frames, for library and generated narration.

    errors: two templates both apply to one frame but say different things; a template
            applied but its sentence wasn't grounded
    warnings: templates that never applied
    coverage: share of frames narrated by a template rather than the neutral sentence
    """
    errors, used, narrated = [], set(), 0
    for view, before in zip(views, befores, strict=True):
        hits = [t for t in templates if applicable(t, view, before)]
        texts = {}
        for t in hits:
            try:
                text, produced = render(t.text, view, before)
            except ExprError:
                continue
            bad = ungrounded_numbers(text, view, produced)
            if bad:
                errors.append(f"template {t.index} at line {t.line}: number(s) {bad} not "
                              f"from the state in {text!r}")  # fmt: skip
            texts[t.index] = text
        if len(set(texts.values())) > 1:
            errors.append(f"line {view.frame['line']}: templates {sorted(texts)} all apply "
                          f"but differ: {sorted(set(texts.values()))}")  # fmt: skip
        if narrate(templates, view, before)["source"] == "template":
            narrated += 1
        used.update(t.index for t in hits)
    warnings = [f"template {t.index} (line {t.line}) never applied"
                for t in templates if t.index not in used]  # fmt: skip
    return {
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "coverage": round(narrated / len(views), 3) if views else 0.0,
    }
