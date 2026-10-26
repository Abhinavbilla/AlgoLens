import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { Frame } from "../api";
import { Markdown } from "./Markdown";
import { MIN_HEIGHT, MIN_WIDTH, clampSize } from "./resize";
import { stepFromFrame, TutorProvider, useTutor, type PageInfo } from "./TutorContext";

const PAGE: PageInfo = {
  target: { kind: "library", id: "kadane" },
  title: "Kadane's algorithm",
  functionName: "max_subarray",
  params: ["nums"],
  suggestions: ["Why does this work?"],
};

type Call = { url: string; body: Record<string, unknown> };
let calls: Call[];

beforeEach(() => {
  sessionStorage.clear();
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? "{}"));
      calls.push({ url, body });
      const reply = url.endsWith("/check")
        ? { verdict: "wrong", passed: 3, total: 30, message: "Passed 3 of 30.", failure: null }
        : { reply: "Line 5 restarts the run with **x**.\n\n```python\ncurrent = x\n```" };
      return new Response(JSON.stringify(reply), { status: 200 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

function StepReporter() {
  const tutor = useTutor();
  return (
    <button
      type="button"
      onClick={() => {
        tutor?.reportStep({ index: 4, line: 5, narration: "current becomes 4", variables: { x: 4 } });
        tutor?.open({ tab: "explain", question: "What's happening here?", withStep: true });
      }}
    >
      step
    </button>
  );
}

test("asks a question and shows the reply with its code", async () => {
  const user = userEvent.setup();
  render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  await user.click(screen.getByRole("button", { name: "Why does this work?" }));
  expect(await screen.findByText(/restarts the run/)).toBeInTheDocument();
  expect(screen.getByText("x").tagName).toBe("STRONG");
  expect(document.querySelector("pre")?.textContent).toBe("current = x");
  expect(calls[0].body).toMatchObject({
    context: { kind: "library", id: "kadane", step: null },
    mode: "explain",
    messages: [{ role: "user", content: "Why does this work?" }],
  });
});

test("ask about this step sends the step on screen", async () => {
  const user = userEvent.setup();
  render(
    <TutorProvider page={PAGE}>
      <StepReporter />
    </TutorProvider>,
  );
  await user.click(screen.getByRole("button", { name: "step" }));
  const box = screen.getByRole("textbox", { name: /your question/i });
  expect(box).toHaveValue("What's happening here?");
  expect(screen.getByRole("checkbox", { name: /include the step/i })).toBeChecked();
  await user.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText(/restarts the run/);
  expect(calls[0].body.context).toMatchObject({ step: { index: 4, line: 5, variables: { x: 4 } } });
  expect(screen.getByText(/about step 5, line 5/i)).toBeInTheDocument();
});

test("hint mode is sent as hint", async () => {
  const user = userEvent.setup();
  render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  await user.click(screen.getByRole("tab", { name: /just a hint/i }));
  await user.type(screen.getByRole("textbox", { name: /your question/i }), "stuck{Enter}");
  await screen.findByText(/restarts the run/);
  expect(calls[0].body.mode).toBe("hint");
});

test("check my code runs the tests, then asks for a review", async () => {
  const user = userEvent.setup();
  render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  await user.click(screen.getByRole("tab", { name: /check my code/i }));
  const editor = screen.getByRole("textbox", { name: /your python code/i });
  expect(editor).toHaveValue("def max_subarray(nums):\n    ");
  await user.click(screen.getByRole("button", { name: "Run the tests" }));
  const verdict = await screen.findByRole("status");
  expect(within(verdict).getByText("Passed 3 of 30.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /ask the tutor why/i }));
  await screen.findByText(/restarts the run/);
  expect(calls[0].url).toBe("/api/chat/check");
  expect(calls[1].body.mode).toBe("review");
  const sent = (calls[1].body.messages as { content: string }[])[0].content;
  expect(sent).toContain("def max_subarray(nums):");
  expect(sent).toContain("Passed 3 of 30.");
});

test("the conversation survives a reload of the page", async () => {
  const user = userEvent.setup();
  const { unmount } = render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  await user.click(screen.getByRole("button", { name: "Why does this work?" }));
  await screen.findByText(/restarts the run/);
  unmount();
  render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  expect(screen.getByText(/restarts the run/)).toBeInTheDocument();
});

test("markdown never renders raw HTML", () => {
  render(<Markdown text={'<img src=x onerror="alert(1)"> and `code`\n\n- one\n- two'} />);
  expect(document.querySelector("img")).toBeNull();
  expect(screen.getByText(/<img/)).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
});

test("a list after a lead-in line is still a list", () => {
  render(<Markdown text={"Here is the logic:\n1. first\n2. second\nSo that's it."} />);
  expect(screen.getByRole("list").tagName).toBe("OL");
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
  expect(screen.getByText("Here is the logic:").tagName).toBe("P");
});

test("a step summary carries the values on screen", () => {
  const frame = {
    i: 2,
    line: 4,
    narration: { text: "best becomes 3", source: "template" },
    panels: [
      { kind: "vars", label: "", items: [{ name: "best", defined: true, value: "3" }] },
      {
        kind: "array",
        label: "nums",
        defined: true,
        items: ["1", "2"],
        pointers: [{ label: "i", index: 1 }],
      },
    ],
  } as unknown as Frame;
  expect(stepFromFrame(frame)).toEqual({
    index: 2,
    line: 4,
    narration: "best becomes 3",
    variables: { best: "3", nums: ["1", "2"], i: 1 },
  });
});

test("the panel can be resized from the keyboard, and the size is remembered", async () => {
  localStorage.removeItem("algolens:tutor-size");
  const user = userEvent.setup();
  const { unmount } = render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  const width = screen.getByRole("separator", { name: /resize the tutor's width/i });
  expect(width).toHaveAttribute("aria-valuenow", "420");
  width.focus();
  await user.keyboard("{ArrowLeft}{ArrowLeft}");
  expect(width).toHaveAttribute("aria-valuenow", "468");
  expect(screen.getByRole("dialog", { name: "Tutor" }).style.getPropertyValue("--tutor-width")).toBe("468px");
  unmount();

  render(<TutorProvider page={PAGE}>page</TutorProvider>);
  await user.click(screen.getByRole("button", { name: /ask the tutor/i }));
  const again = screen.getByRole("separator", { name: /resize the tutor's width/i });
  expect(again).toHaveAttribute("aria-valuenow", "468");
  await user.dblClick(again);
  expect(again).toHaveAttribute("aria-valuenow", "420");
});

test("a size never goes below the minimum or past the window", () => {
  expect(clampSize({ width: 100, height: 100 }, 1280, 900)).toEqual({ width: MIN_WIDTH, height: MIN_HEIGHT });
  expect(clampSize({ width: 5000, height: 600 }, 1280, 900)).toEqual({ width: 1248, height: 600 });
  expect(clampSize({ width: 500, height: 866 }, 1280, 900)).toEqual({ width: 500, height: null }); // full height again
});
