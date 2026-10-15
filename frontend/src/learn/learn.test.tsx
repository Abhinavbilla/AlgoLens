import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App } from "../App";
import { PATH, PRIMERS } from "./path";
import { PRACTICE } from "./practice";

const LIBRARY = ["bubble-sort", "insertion-sort", "binary-search", "two-pointers"].map((slug) => ({
  slug,
  title: slug.replace("-", " "),
  category: "Sorting",
  summary: `About ${slug}.`,
  verification: { status: "verified", tests: 310 },
}));

function mockApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/health") return { ok: true, json: async () => ({ status: "ok" }) };
      if (url === "/api/library") return { ok: true, json: async () => LIBRARY };
      return { ok: false, status: 404, json: async () => ({ detail: "not found" }) };
    }),
  );
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());

const said = () =>
  screen
    .getAllByRole("status")
    .map((e) => e.textContent)
    .join(" | ");
afterEach(() => vi.unstubAllGlobals());

test("the path lists stages in order, skips what isn't in the library, and tracks progress", async () => {
  mockApi();
  renderAt("/path");
  expect(await screen.findByText("Foundations")).toBeInTheDocument();
  expect(screen.getByText("Your first algorithms")).toBeInTheDocument();
  expect(screen.queryByText("Going further")).not.toBeInTheDocument(); // none of its entries are here
  expect(screen.getByText(/0 of 17 done/)).toBeInTheDocument(); // 13 primers + 4 present entries
  expect(screen.getByText(/Next up:/)).toHaveTextContent("Arrays and indexes");
  await userEvent.click(screen.getByRole("button", { name: "Arrays and indexes: not done" }));
  expect(screen.getByText(/1 of 17 done/)).toBeInTheDocument();
  expect(screen.getByText(/Next up:/)).toHaveTextContent("Big-O");
  expect(JSON.parse(localStorage.getItem("algolens.done") ?? "[]")).toEqual(["primer:arrays"]);
});

test("a primer explains, checks understanding, and links onward", async () => {
  mockApi();
  renderAt("/learn/arrays");
  expect(screen.getByRole("heading", { level: 1, name: "Arrays and indexes" })).toBeInTheDocument();
  const check = screen.getByRole("complementary", { name: "Check yourself" });
  await userEvent.click(within(check).getByRole("button", { name: "Show the answer" }));
  expect(check).toHaveTextContent("the last index is 4");
  expect(screen.getByRole("link", { name: "Next on the path →" })).toHaveAttribute("href", "/learn/big-o");
  await userEvent.click(screen.getByRole("button", { name: "Mark as done" }));
  expect(screen.getByRole("button", { name: "✓ Marked as done" })).toHaveAttribute("aria-pressed", "true");
});

test("the Big-O table is computed, not typed in", () => {
  mockApi();
  renderAt("/learn/big-o");
  expect(screen.getByRole("table")).toHaveTextContent("10,000,000,000"); // 100,000²
});

test("every path item and practice list points at something real", () => {
  for (const stage of PATH) {
    for (const item of stage.items) {
      if (item.startsWith("primer:")) expect(PRIMERS[item.slice(7)]).toBeDefined();
    }
  }
  for (const [slug, list] of Object.entries(PRACTICE)) {
    expect(list.length, slug).toBeGreaterThan(0);
    for (const p of list)
      expect(p.url).toMatch(
        /^https:\/\/(leetcode\.com\/problems\/[a-z0-9-]+\/|codeforces\.com\/problemset\/problem\/\d+\/[A-Z])$/,
      );
  }
});

test("stack and queue hand things back in opposite orders", async () => {
  mockApi();
  renderAt("/learn/stacks-queues");
  await userEvent.click(screen.getByRole("button", { name: "Take one out of each" }));
  expect(
    screen.getByText(/stack gave back 3, the last one in.*queue gave back 1, the first one in/),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Add 4 to both" }));
  expect(screen.getByRole("list", { name: /Stack, bottom to top: 1, 2, 4/ })).toBeInTheDocument();
  expect(screen.getByRole("list", { name: /Queue, front to back: 2, 3, 4/ })).toBeInTheDocument();
});

test("the hash demo shows the arithmetic and the bucket", async () => {
  mockApi();
  renderAt("/learn/hashing");
  const input = screen.getByRole("textbox", { name: "Word" });
  await userEvent.clear(input);
  await userEvent.type(input, "ab");
  expect(screen.getByText(/97 \+ 98 = 195; 195 mod 7 =/)).toHaveTextContent("bucket 6");
  await userEvent.click(screen.getByRole("button", { name: "Store it" }));
  expect(said()).toContain('"ab"');
});

test("linked list: reaching the end means following every arrow", async () => {
  mockApi();
  renderAt("/learn/linked-lists");
  await userEvent.click(screen.getByRole("button", { name: "Add 5 at the front" }));
  await userEvent.click(screen.getByRole("button", { name: "Find the last node" }));
  expect(said()).toContain("follow 4 arrows");
});

test("graph demo lists each node's neighbours", async () => {
  mockApi();
  renderAt("/learn/graphs");
  await userEvent.click(screen.getByRole("button", { name: "1" }));
  expect(said()).toContain("Node 1 is connected to 0, 2 and 4");
});

test("tree demo names a node's role", async () => {
  mockApi();
  renderAt("/learn/trees");
  await userEvent.click(screen.getByRole("button", { name: "8" }));
  expect(said()).toContain("the root");
});

test("strings: a slice is start up to but not including end", () => {
  mockApi();
  renderAt("/learn/strings");
  expect(said()).toContain('s[2:6] is "gori"');
  expect(said()).toContain("1 + 2 + … + 10 = 55 characters");
});

test("sets: operations and membership", async () => {
  mockApi();
  renderAt("/learn/sets");
  expect(said()).toContain("A & B is {4, 5}");
  await userEvent.click(screen.getByRole("button", { name: "A | B" }));
  expect(said()).toContain("A | B is {1, 2, 3, 4, 5, 6, 7}");
  await userEvent.click(screen.getByRole("button", { name: "A - B" }));
  expect(said()).toContain("A - B is {1, 2, 3}");
  expect(said()).toContain("No: 6 in A is False");
});

test("bits: flipping, shifting and clearing the lowest one-bit", async () => {
  mockApi();
  renderAt("/learn/bits");
  expect(screen.getByRole("list", { name: "44 in binary: 00101100" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "n & (n - 1)" }));
  expect(screen.getByRole("list", { name: "40 in binary: 00101000" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "bit worth 1: 0" }));
  expect(said()).toContain("giving 41");
  expect(said()).toContain("41 is odd");
});

test("numbers: modulo and digits", async () => {
  mockApi();
  renderAt("/learn/numbers");
  expect(said()).toContain("23 mod 7 = 2");
  for (let i = 0; i < 4; i++)
    await userEvent.click(screen.getByRole("button", { name: "Take the last digit" }));
  expect(said()).toContain("4096 has 4 digits");
});

test("stability keeps ties in their original order", async () => {
  mockApi();
  renderAt("/learn/stable-sorting");
  await userEvent.click(screen.getByRole("button", { name: "Sort by grade, stable" }));
  const order = within(screen.getByRole("list", { name: "Students in the current order" }))
    .getAllByRole("listitem")
    .map((li) => li.querySelector("strong")?.textContent);
  expect(order).toEqual(["Ben", "Dev", "Asha", "Chen", "Ema"]);
});
