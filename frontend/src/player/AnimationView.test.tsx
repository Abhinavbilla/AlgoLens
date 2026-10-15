import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Animation, Frame } from "../api";
import { AnimationView } from "./AnimationView";
import { stepDurationMs } from "./playerState";

const PY = "def f(l, r):\n    l += 1\n    return l\n";
const CPP = "int f(int l, int r) {\n    l += 1;\n    return l;\n}\n";

function frame(i: number, over: Partial<Frame>): Frame {
  return {
    i,
    line: 2,
    next: 3,
    cpp_line: 2,
    code: "l += 1",
    ops: i + 1,
    aid: 0,
    stack: [{ aid: 0, fn: "f", line: 2, call: "f(l=0, r=3)", new: i === 0 }],
    panels: [],
    narration: { text: `step ${i}`, source: "template" },
    ...over,
  };
}

const ANIMATION: Animation = {
  total_ops: 3,
  result: 1,
  input: { args: [0, 3] },
  frames: [
    frame(0, {
      narration: { text: "Start with l at 0.", source: "template" },
      panels: [
        {
          kind: "array",
          label: "nums",
          defined: true,
          items: ["1", "3", "4"],
          changed: [],
          pointers: [
            { label: "l", index: 0 },
            { label: "r", index: 2 },
          ],
        },
        {
          kind: "vars",
          label: "Variables",
          items: [{ name: "l", defined: true, value: "0", changed: false }],
        },
      ],
    }),
    frame(1, {
      narration: { text: "l moves from 0 to 1.", source: "template" },
      panels: [
        {
          kind: "array",
          label: "nums",
          defined: true,
          items: ["1", "3", "9"],
          changed: [2],
          pointers: [
            { label: "l", index: 1 },
            { label: "r", index: 2 },
          ],
        },
        {
          kind: "vars",
          label: "Variables",
          items: [{ name: "l", defined: true, value: "1", changed: true }],
        },
      ],
    }),
    frame(2, {
      line: 3,
      next: "return",
      cpp_line: 3,
      code: "return l",
      narration: { text: "Return 1.", source: "template" },
      ret: "1",
    }),
  ],
};

function renderPlayer() {
  return render(<AnimationView animation={ANIMATION} python={PY} cpp={CPP} />);
}

// The sentence currently shown (the others are laid out invisibly to reserve height).
const narration = () => document.querySelector("[data-current-narration] p") as HTMLElement;

afterEach(() => vi.useRealTimers());

test("shows the first step's narration, panels and position", () => {
  renderPlayer();
  expect(narration()).toHaveTextContent("Start with l at 0.");
  expect(screen.getByText("Step 1 of 3 · 1 operation so far")).toBeInTheDocument();
  const array = screen.getByRole("region", { name: "nums" });
  expect(within(array).getByText("l")).toBeInTheDocument();
  expect(within(array).getByText("r")).toBeInTheDocument();
});

test("arrow keys step forward and back, and Home/End jump", async () => {
  renderPlayer();
  await userEvent.keyboard("{ArrowRight}");
  expect(narration()).toHaveTextContent("l moves from 0 to 1.");
  await userEvent.keyboard("{ArrowLeft}");
  expect(narration()).toHaveTextContent("Start with l at 0.");
  await userEvent.keyboard("{End}");
  expect(narration()).toHaveTextContent("Return 1.");
  await userEvent.keyboard("{Home}");
  expect(narration()).toHaveTextContent("Start with l at 0.");
});

test("changed values are marked in text, not only by colour", async () => {
  renderPlayer();
  await userEvent.keyboard("{ArrowRight}");
  const array = screen.getByRole("region", { name: "nums" });
  expect(within(array).getAllByText("(changed)")).toHaveLength(1);
  const vars = screen.getByRole("region", { name: "Variables" });
  expect(within(vars).getByText("(changed)")).toBeInTheDocument();
});

test("the current line is highlighted in both languages", async () => {
  renderPlayer();
  const code = screen.getByRole("region", { name: "Code" });
  const current = () => code.querySelector('[aria-current="step"]');
  expect(current()).toHaveTextContent("l += 1");
  await userEvent.keyboard("{End}");
  expect(current()).toHaveTextContent("return l");
  await userEvent.click(within(code).getByRole("button", { name: "C++" }));
  expect(current()).toHaveTextContent("return l;");
});

test("Space plays to the end at the chosen speed", () => {
  vi.useFakeTimers();
  renderPlayer();
  fireEvent.change(screen.getByRole("combobox", { name: "Speed" }), { target: { value: "2" } });
  fireEvent.keyDown(window, { key: " " });
  expect(screen.getByRole("button", { name: /Pause/ })).toBeInTheDocument();
  // Each step stays up for its own sentence's reading time, divided by the speed.
  act(() => vi.advanceTimersByTime(stepDurationMs("Start with l at 0.", 2) - 1));
  expect(narration()).toHaveTextContent("Start with l at 0.");
  act(() => vi.advanceTimersByTime(1));
  expect(narration()).toHaveTextContent("l moves from 0 to 1.");
  act(() => vi.advanceTimersByTime(stepDurationMs("l moves from 0 to 1.", 2)));
  expect(narration()).toHaveTextContent("Return 1.");
  expect(screen.getByRole("button", { name: /Play/ })).toBeInTheDocument();
});

test("the step slider seeks", () => {
  renderPlayer();
  fireEvent.change(screen.getByRole("slider", { name: "Step" }), { target: { value: "2" } });
  expect(narration()).toHaveTextContent("Return 1.");
});

test("call stack shows the running call with a text marker", () => {
  renderPlayer();
  const stack = screen.getByRole("region", { name: "Call stack" });
  expect(within(stack).getByText("f(l=0, r=3)")).toBeInTheDocument();
  expect(within(stack).getByText("new")).toBeInTheDocument();
  expect(within(stack).getByText("(running)")).toBeInTheDocument();
});

test("the narration box is announced only while not playing", () => {
  vi.useFakeTimers();
  renderPlayer();
  const box = narration().closest("[aria-live]") as HTMLElement;
  expect(box).toHaveAttribute("aria-live", "polite");
  fireEvent.keyDown(window, { key: " " });
  expect(box).toHaveAttribute("aria-live", "off");
});
