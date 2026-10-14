import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App } from "./App";

const LIBRARY = [
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
  expect(await screen.findByRole("link", { name: "Two pointers" })).toHaveAttribute("href", "/library/two-pointers");
  expect(screen.getByText(/Verified · passed 11 tests/)).toBeInTheDocument();
});

test("navigates to the paste page", async () => {
  mockApi();
  renderAt("/");
  await userEvent.click(screen.getByRole("link", { name: "Paste a problem" }));
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
