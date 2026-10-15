import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App } from "./App";

const LIBRARY = [
  {
    slug: "bubble-sort",
    title: "Bubble sort",
    category: "Sorting",
    summary: "Swap neighbours.",
    verification: { status: "verified", tests: 310 },
  },
  {
    slug: "dijkstra",
    title: "Dijkstra's shortest paths",
    category: "Graphs and grids",
    summary: "Cheapest first.",
    verification: { status: "unverified" },
  },
  {
    slug: "two-pointers",
    title: "Two pointers",
    category: "Two pointers",
    summary: "Move in from both ends.",
    verification: { status: "verified", tests: 11 },
  },
];

function mockApi(health: "ok" | "down" | "unreachable" = "ok") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/health") {
        if (health === "unreachable") throw new Error("down");
        return { ok: true, json: async () => ({ status: health === "ok" ? "ok" : "degraded" }) };
      }
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

afterEach(() => vi.unstubAllGlobals());

test("shows server OK when health check passes", async () => {
  mockApi("ok");
  renderAt("/");
  expect(screen.getByRole("heading", { name: "Algorithm library" })).toBeInTheDocument();
  expect(await screen.findByText("Server OK")).toBeInTheDocument();
});

test("shows a text label when the server is unreachable", async () => {
  mockApi("unreachable");
  renderAt("/");
  expect(await screen.findByText("Server unreachable")).toBeInTheDocument();
});

test("lists library entries with their verification status in text", async () => {
  mockApi();
  renderAt("/");
  expect(await screen.findByRole("link", { name: "Two pointers" })).toHaveAttribute(
    "href",
    "/library/two-pointers",
  );
  expect(screen.getByText(/Verified · 11 tests/)).toBeInTheDocument();
});

test("navigates to the paste page", async () => {
  mockApi();
  renderAt("/");
  const nav = screen.getByRole("navigation", { name: "Main" });
  await userEvent.click(within(nav).getByRole("link", { name: "Paste a problem" }));
  expect(screen.getByRole("heading", { name: "Paste a problem" })).toBeInTheDocument();
});

test("theme toggle cycles and sets data-theme", async () => {
  mockApi();
  renderAt("/");
  const button = screen.getByRole("button", { name: /Theme:/ });
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBe("light");
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBe("dark");
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBeUndefined();
});

test("description markdown renders as elements, never as raw HTML", async () => {
  const { InlineMarkdown } = await import("./InlineMarkdown");
  const { container } = render(<InlineMarkdown text={"Move `l` right, a *lower bound*, <b>not bold</b>"} />);
  expect(container.querySelector("code")).toHaveTextContent("l");
  expect(container.querySelector("em")).toHaveTextContent("lower bound");
  expect(container.querySelector("b")).toBeNull();
  expect(container).toHaveTextContent("<b>not bold</b>");
});

test("the library is grouped into sections with a jump bar", async () => {
  mockApi();
  renderAt("/");
  const sorting = await screen.findByRole("region", { name: "Sorting" });
  expect(within(sorting).getByRole("link", { name: "Bubble sort" })).toBeInTheDocument();
  expect(
    within(screen.getByRole("region", { name: "Array techniques" })).getByText("Two pointers", {
      selector: "a",
    }),
  ).toBeInTheDocument();
  const jump = screen.getByRole("navigation", { name: "Library sections" });
  expect(within(jump).getByRole("link", { name: /Graphs and grids/ })).toHaveAttribute("href", "#graphs");
  expect(screen.getByText(/3 algorithms, 2 verified/)).toBeInTheDocument();
  expect(screen.getByText("Not verified yet")).toBeInTheDocument();
});

test("search filters the library", async () => {
  mockApi();
  renderAt("/");
  await screen.findByRole("region", { name: "Sorting" });
  await userEvent.type(screen.getByRole("searchbox", { name: "Search the library" }), "cheapest");
  expect(screen.getByRole("link", { name: "Dijkstra's shortest paths" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Bubble sort" })).not.toBeInTheDocument();
  await userEvent.clear(screen.getByRole("searchbox", { name: "Search the library" }));
  await userEvent.type(screen.getByRole("searchbox", { name: "Search the library" }), "zzz");
  expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
});

test("the hero shows a real bubble sort with narration", async () => {
  mockApi();
  renderAt("/");
  const preview = screen.getByRole("figure", { name: /bubble sort running/ });
  expect(preview).toHaveTextContent("Unsorted. Let's bubble.");
});
