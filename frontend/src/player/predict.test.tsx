import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Animation, Frame } from "../api";
import { AnimationView } from "./AnimationView";
import { decisionTargets, questionAt } from "./predict";

const PY = "def f(x):\n    x = 0\n    while x < 2:\n        x += 1\n    return x\n";

function frame(i: number, line: number, next: Frame["next"], text: string, code: string): Frame {
  return {
    i,
    line,
    next,
    cpp_line: null,
    code,
    ops: i + 1,
    aid: 0,
    stack: [{ aid: 0, fn: "f", line, call: "f(x=0)", new: i === 0 }],
    panels: [],
    narration: { text, source: "template" },
  };
}

// The while loop on line 3 continues once (to line 4) and then ends (to line 5).
const FRAMES = [
  frame(0, 2, 3, "Start at 0.", "x = 0"),
  frame(1, 3, 4, "0 < 2, so loop.", "while x < 2:"),
  frame(2, 4, 3, "x is now 1.", "x += 1"),
  frame(3, 3, 5, "Stop looping.", "while x < 2:"),
  frame(4, 5, "return", "Return 1.", "return x"),
];
const ANIMATION: Animation = { frames: FRAMES, total_ops: 5, result: 1, input: { args: [0] } };

test("questions come only from lines that went more than one way", () => {
  const targets = decisionTargets(FRAMES);
  expect(targets.get(3)).toEqual([4, 5]);
  expect(questionAt(FRAMES, targets, 0)).toBeNull(); // line 2 always goes to 3
  expect(questionAt(FRAMES, targets, 1)).toEqual({ index: 1, line: 3, answer: 4, choices: [4, 5] });
  expect(questionAt(FRAMES, targets, 3)?.answer).toBe(5);
  expect(questionAt(FRAMES, targets, 4)).toBeNull(); // the last step
});

test("predict mode asks before revealing, then scores the answer", async () => {
  render(<AnimationView animation={ANIMATION} python={PY} cpp="" />);
  await userEvent.click(screen.getByRole("button", { name: "Predict the next step" }));
  expect(screen.getByRole("button", { name: "Predict mode: on" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.keyboard("{ArrowRight}"); // to the loop check
  const question = screen.getByRole("group", { name: /Line 3 just ran.*Where does the code go next/ });
  expect(screen.queryByText("0 < 2, so loop.")).not.toBeVisible(); // the sentence would give it away
  await userEvent.click(screen.getByRole("button", { name: /Line 5: return x/ }));
  expect(question).not.toBeInTheDocument();
  expect(screen.getByText(/Not quite: it went to line 4/)).toBeInTheDocument();
  expect(screen.getByText("0 of 1 predicted right")).toBeInTheDocument();
  await userEvent.keyboard("{ArrowRight}{ArrowRight}"); // the check again, now ending the loop
  await userEvent.click(screen.getByRole("button", { name: /Line 5: return x/ }));
  expect(screen.getByText("✓ Right.")).toBeInTheDocument();
  expect(screen.getByText("1 of 2 predicted right")).toBeInTheDocument();
});

test("without predict mode nothing is asked", async () => {
  render(<AnimationView animation={ANIMATION} python={PY} cpp="" />);
  await userEvent.keyboard("{ArrowRight}");
  expect(screen.queryByRole("group", { name: /Where does the code go next/ })).not.toBeInTheDocument();
});
