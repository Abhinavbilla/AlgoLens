import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App } from "../App";

const STATEMENT = "Given an integer array nums, return the largest subarray sum. Example: [1] -> 1";

const APPROACH = {
  id: "a1",
  name: "Kadane",
  key_idea: "Extend or restart the running sum.",
  time: "O(n)",
  space: "O(1)",
  python_code: "def f(nums):\n    return 1\n",
  cpp_code: "int main() {}\n",
  status: "verified",
  is_brute: false,
  reason: "",
  tests_passed: 300,
  tests_total: 300,
  examples_checked: 2,
  repairs: 1,
  failing_case: null,
  animated: true,
  animation_note: "",
  default_input: { args: [[1]] },
};

const PROBLEM = {
  id: "p1",
  status: "done",
  reason: "",
  title: "Maximum Subarray",
  function_name: "max_sub_array",
  params: [{ name: "nums" }],
  examples: [],
  comparator: "exact",
  inputs: [{ name: "nums", kind: "array", hint: "a list of 1 to 100000 integers" }],
  approaches: [
    { ...APPROACH, id: "a0", name: "Brute force", is_brute: true, repairs: 0 },
    APPROACH,
    {
      ...APPROACH,
      id: "a2",
      name: "Divide and conquer",
      status: "unverified",
      reason: "Wrong on input [[-1]]: expected -1, got 0",
      tests_passed: 0,
      repairs: 2,
      animated: false,
      animation_note: "Only verified approaches are animated.",
    },
  ],
};

type Route = (url: string, init?: RequestInit) => { status: number; body: unknown } | undefined;

function mockApi(route: Route) {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      const r =
        route(url, init) ??
        (url === "/api/health"
          ? { status: 200, body: { status: "ok" } }
          : { status: 404, body: { detail: "not found" } });
      return { ok: r.status < 400, status: r.status, json: async () => r.body };
    }),
  );
  return calls;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("submitting a cached problem goes straight to its result", async () => {
  const calls = mockApi((url) => {
    if (url === "/api/problems") return { status: 200, body: { problem_id: "p1" } };
    if (url === "/api/problems/p1") return { status: 200, body: PROBLEM };
  });
  renderAt("/solve");
  const button = screen.getByRole("button", { name: "Solve and verify" });
  expect(button).toBeDisabled();
  await userEvent.click(screen.getByLabelText("Problem statement"));
  await userEvent.paste(STATEMENT);
  await userEvent.click(button);
  expect(await screen.findByRole("heading", { name: "Maximum Subarray" })).toBeInTheDocument();
  const post = calls.find((c) => c.url === "/api/problems");
  expect(JSON.parse(String(post?.init?.body))).toEqual({ text: STATEMENT });
});

test("the server's reason is shown when solving isn't available", async () => {
  mockApi((url) => {
    if (url === "/api/problems")
      return {
        status: 503,
        body: {
          detail: "Solving new problems isn't set up yet (missing GEMINI_API_KEY).",
        },
      };
  });
  renderAt("/solve");
  await userEvent.click(screen.getByLabelText("Problem statement"));
  await userEvent.paste(STATEMENT);
  await userEvent.click(screen.getByRole("button", { name: "Solve and verify" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("missing GEMINI_API_KEY");
});

test("the character count warns past the limit", async () => {
  mockApi(() => undefined);
  renderAt("/solve");
  const box = screen.getByLabelText("Problem statement");
  await userEvent.click(box);
  await userEvent.paste("x".repeat(10_001));
  expect(screen.getByText("10,001 / 10,000 characters")).toBeInTheDocument();
  expect(box).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("button", { name: "Solve and verify" })).toBeDisabled();
});

test("each approach shows its verification status in words", async () => {
  mockApi((url) => (url === "/api/problems/p1" ? { status: 200, body: PROBLEM } : undefined));
  renderAt("/problems/p1");
  expect(await screen.findByRole("heading", { name: /Brute force/ })).toBeInTheDocument();
  expect(screen.getAllByText(/Verified · 2 examples and 300 random tests/)).toHaveLength(2);
  expect(screen.getByText(/Not verified$/)).toBeInTheDocument();
  expect(screen.getByText("Wrong on input [[-1]]: expected -1, got 0")).toBeInTheDocument();
  expect(screen.getByText(/fixed once after failing a check/)).toBeInTheDocument();
  expect(screen.getByText(/fixed 2 times/)).toBeInTheDocument();
});

test("code switches between Python and C++", async () => {
  mockApi((url) =>
    url === "/api/problems/p1" ? { status: 200, body: { ...PROBLEM, approaches: [APPROACH] } } : undefined,
  );
  renderAt("/problems/p1");
  expect(await screen.findByRole("tabpanel")).toHaveTextContent("def f(nums): return 1");
  expect(screen.getByRole("tabpanel").querySelector("span")).toHaveTextContent("def"); // highlighted
  await userEvent.click(screen.getByRole("tab", { name: "C++" }));
  expect(screen.getByRole("tabpanel")).toHaveTextContent("int main() {}");
  expect(screen.getByRole("tab", { name: "C++" })).toHaveAttribute("aria-selected", "true");
});

test("a rejected problem shows why", async () => {
  mockApi((url) =>
    url === "/api/problems/p2"
      ? {
          status: 200,
          body: {
            ...PROBLEM,
            id: "p2",
            status: "rejected",
            reason: "This is a geometry proof.",
            approaches: [],
          },
        }
      : undefined,
  );
  renderAt("/problems/p2");
  expect(
    await screen.findByRole("heading", {
      name: "This problem isn't supported",
    }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("This is a geometry proof.");
});

test("job progress is polled when there's no event stream, then opens the result", async () => {
  vi.stubGlobal("EventSource", undefined);
  let n = 0;
  mockApi((url) => {
    if (url === "/api/jobs/j1") {
      n += 1;
      return n === 1
        ? {
            status: 200,
            body: {
              id: "j1",
              status: "running",
              stage: "checking Kadane",
              tests_passed: 100,
              tests_total: 302,
              error: "",
              problem_id: null,
            },
          }
        : {
            status: 200,
            body: {
              id: "j1",
              status: "done",
              stage: "finished",
              tests_passed: 0,
              tests_total: 0,
              error: "",
              problem_id: "p1",
            },
          };
    }
    if (url === "/api/problems/p1") return { status: 200, body: PROBLEM };
  });
  renderAt("/jobs/j1");
  expect(await screen.findByText("Checking Kadane")).toBeInTheDocument();
  expect(screen.getByText("100 of 302 tests run")).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "Maximum Subarray" }, { timeout: 4000 }),
  ).toBeInTheDocument();
});

test("a failed job says nothing was judged", async () => {
  vi.stubGlobal("EventSource", undefined);
  mockApi((url) =>
    url === "/api/jobs/j2"
      ? {
          status: 200,
          body: {
            id: "j2",
            status: "failed",
            stage: "",
            tests_passed: 0,
            tests_total: 0,
            error: "the code runner is down",
            problem_id: null,
          },
        }
      : undefined,
  );
  renderAt("/jobs/j2");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("the code runner is down");
  expect(alert).toHaveTextContent("Nothing was marked verified or wrong");
});

const FRAME = {
  i: 0,
  line: 2,
  next: "return",
  cpp_line: null,
  code: "return 1",
  ops: 1,
  aid: 0,
  stack: [{ aid: 0, fn: "f", line: 2, call: "f(nums=[1])", new: true }],
  panels: [],
  narration: { text: "The best sum so far is 1.", source: "template" },
  ret: "1",
};

test("a verified approach can be watched step by step; unverified ones say why not", async () => {
  mockApi((url) => {
    if (url === "/api/problems/p1") return { status: 200, body: PROBLEM };
    if (url === "/api/problems/p1/approaches/a1/animation")
      return { status: 200, body: { frames: [FRAME], total_ops: 1, result: 1, input: { args: [[1]] } } };
  });
  renderAt("/problems/p1");
  expect(await screen.findByText("Only verified approaches are animated.")).toBeInTheDocument();
  const buttons = screen.getAllByRole("button", { name: "Watch it run step by step" });
  expect(buttons).toHaveLength(2); // the brute force and Kadane
  await userEvent.click(buttons[1]);
  expect(await screen.findAllByText("The best sum so far is 1.")).not.toHaveLength(0);
  expect(screen.getByRole("button", { name: "Show the code only" })).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByLabelText(/nums/)).toBeInTheDocument(); // the custom input editor
});

test("the comparison runs on request and shows a chart, a legend and the numbers", async () => {
  mockApi((url) => {
    if (url === "/api/problems/p1") return { status: 200, body: PROBLEM };
    if (url === "/api/problems/p1/compare")
      return {
        status: 200,
        body: {
          sizes: [10, 100, 1000, 3000],
          limits: { cpu_ms: 4000 },
          series: [
            {
              id: "a0",
              name: "Brute force",
              points: [
                { n: 10, ops: 170, status: "ok" },
                { n: 100, ops: 15200, status: "ok" },
                { n: 1000, ops: 1502000, status: "ok" },
                { n: 3000, ops: null, status: "too slow" },
              ],
            },
            {
              id: "a1",
              name: "Kadane",
              points: [10, 100, 1000, 3000].map((n) => ({ n, ops: 3 * n + 4, status: "ok" })),
            },
          ],
        },
      };
  });
  renderAt("/problems/p1");
  await userEvent.click(await screen.findByRole("button", { name: "Run the comparison" }));
  expect(await screen.findByRole("img", { name: /Lines executed against input size/ })).toBeInTheDocument();
  expect(screen.getByText(/stopped: too slow from n = 3000 with a 4 s limit/)).toBeInTheDocument();
  const table = screen.getByRole("table", { name: "Lines executed at each size" });
  expect(table).toHaveTextContent("1,502,000");
  expect(table).toHaveTextContent("too slow");
  expect(table).toHaveTextContent("9,004");
});

test("an exhaustively tested approach says so", async () => {
  mockApi((url) =>
    url === "/api/problems/p1"
      ? { status: 200, body: { ...PROBLEM, approaches: [{ ...APPROACH, exhaustive: true, tests_passed: 45 }] } }
      : undefined,
  );
  renderAt("/problems/p1");
  expect(await screen.findByText(/all 45 possible inputs/)).toBeInTheDocument();
});
