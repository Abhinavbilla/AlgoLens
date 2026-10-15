import type { Frame } from "../api";

// "Predict the next step": questions built only from the recording itself. A step becomes a
// question when its line went to different places at different times in this run (an `if`
// that was sometimes true and sometimes false, a loop that sometimes continued and once
// ended). The choices are exactly those places, so every option is real and exactly one is
// what happened at this step.

export type Target = number | "return";
export type Question = { index: number; line: number; answer: Target; choices: Target[] };

export function decisionTargets(frames: Frame[]): Map<number, Target[]> {
  const seen = new Map<number, Target[]>();
  for (const f of frames) {
    if (f.next === null) continue;
    const list = seen.get(f.line) ?? [];
    if (!list.includes(f.next)) list.push(f.next);
    seen.set(f.line, list);
  }
  return seen;
}

export function questionAt(frames: Frame[], targets: Map<number, Target[]>, index: number): Question | null {
  const f = frames[index];
  if (!f || f.next === null || index === frames.length - 1) return null;
  const choices = targets.get(f.line) ?? [];
  if (choices.length < 2) return null;
  const sorted = [...choices].sort((a, b) => order(a) - order(b));
  return { index, line: f.line, answer: f.next, choices: sorted };
}

const order = (t: Target) => (t === "return" ? Number.MAX_SAFE_INTEGER : t);
