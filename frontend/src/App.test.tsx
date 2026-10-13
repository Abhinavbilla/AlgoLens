import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { App } from "./App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("shows server OK when health check passes", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => ({ status: "ok" }) }));
  renderAt("/");
  expect(screen.getByRole("heading", { name: "Algorithm library" })).toBeInTheDocument();
  expect(await screen.findByText("Server OK")).toBeInTheDocument();
});

test("shows a text label when the server is unreachable", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
  renderAt("/");
  expect(await screen.findByText("Server unreachable")).toBeInTheDocument();
});

test("navigates to the paste page", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => ({ status: "ok" }) }));
  renderAt("/");
  await userEvent.click(screen.getByRole("link", { name: "Paste a problem" }));
  expect(screen.getByRole("heading", { name: "Paste a problem" })).toBeInTheDocument();
});

test("theme toggle cycles and sets data-theme", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => ({ status: "ok" }) }));
  renderAt("/");
  const button = screen.getByRole("button", { name: /Theme:/ });
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBe("light");
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBe("dark");
  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBeUndefined();
});
