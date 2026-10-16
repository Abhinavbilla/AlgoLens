import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../App";

const USER = { id: "u1", email: "ada@example.com", name: "Ada Learner", picture: "" };

type Call = { url: string; method: string; headers: Record<string, string>; body: unknown };
let calls: Call[];

type Me = { enabled: boolean; google?: boolean; email?: boolean; user: typeof USER | null };

function mockApi(me: Me, serverDone: string[] = []) {
  me = { google: me.enabled, email: me.enabled, ...me };
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({
        url,
        method,
        headers: (init?.headers ?? {}) as Record<string, string>,
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
      });
      const json = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
      if (url === "/api/auth/me" && method === "GET") return json(me);
      if (url === "/api/auth/me" && method === "DELETE") return json({ deleted: true });
      if (url === "/api/auth/logout") return json({ user: null });
      if (url === "/api/me/progress" && method === "GET") return json({ done: serverDone });
      if (url === "/api/me/progress") return json({ done: [] });
      if (url === "/api/me/problems") return json([]);
      if (url === "/api/auth/email/start") return json({ sent: true, minutes: 10 });
      if (url === "/api/auth/email/verify") {
        const { code } = JSON.parse(String(init?.body));
        return code === "123456"
          ? json({ user: { ...USER, email: "new@example.com", name: "new" } })
          : json({ detail: "That code isn't right, or it has expired." }, 401);
      }
      if (url === "/api/health") return json({ status: "ok" });
      return json({ detail: "not found" }, 404);
    }),
  );
}

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

test("no sign-in button when sign-in isn't set up", async () => {
  mockApi({ enabled: false, user: null });
  renderAt("/library");
  await waitFor(() => expect(calls.some((c) => c.url === "/api/auth/me")).toBe(true));
  expect(screen.queryByRole("link", { name: "Log in" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Sign up" })).toBeNull();
});

test("signed out: sign-in is offered, and nothing else needs it", async () => {
  mockApi({ enabled: true, user: null });
  const assign = vi.fn();
  vi.stubGlobal("location", { ...window.location, assign, pathname: "/account", search: "" });
  renderAt("/account");
  expect(await screen.findByText(/continue without an account/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /log in with google/i }));
  expect(assign).toHaveBeenCalledWith("/api/auth/google/login?next=%2Faccount");
});

test("the header's sign-in comes back to the page you were on", async () => {
  mockApi({ enabled: true, user: null });
  renderAt("/library/kadane");
  const login = await screen.findByRole("link", { name: "Log in" });
  expect(login).toHaveAttribute("href", "/account?mode=login&next=%2Flibrary%2Fkadane");
  const signup = screen.getByRole("link", { name: "Sign up" });
  expect(signup).toHaveAttribute("href", "/account?mode=signup&next=%2Flibrary%2Fkadane");
});

test("only the ways that are set up are offered", async () => {
  mockApi({ enabled: true, google: false, email: true, user: null });
  renderAt("/account");
  expect(await screen.findByLabelText(/your email/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /with google/i })).toBeNull();
});

test("signing in with an emailed code", async () => {
  mockApi({ enabled: true, user: null });
  const user = userEvent.setup();
  renderAt("/account?next=/path");
  await user.type(await screen.findByLabelText(/your email/i), "new@example.com");
  await user.click(screen.getByRole("button", { name: /log in with email/i }));
  expect(await screen.findByText(/code sent to/i)).toHaveTextContent("new@example.com");
  const box = screen.getByLabelText("Code");
  await user.type(box, "999999");
  await user.click(screen.getByRole("button", { name: "Verify & log in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/isn't right/);
  await user.clear(box);
  await user.type(box, "123456");
  await user.click(screen.getByRole("button", { name: "Verify & log in" }));
  expect(await screen.findByRole("link", { name: /your account \(new\)/i })).toBeInTheDocument();
  const start = calls.find((c) => c.url === "/api/auth/email/start")!;
  expect(start.body).toEqual({ email: "new@example.com" });
  expect(start.headers["X-Requested-With"]).toBe("algolens");
});

test("a failed sign-in explains why", async () => {
  mockApi({ enabled: true, user: null });
  renderAt("/account?error=Sign-in%20was%20cancelled.");
  expect(await screen.findByRole("alert")).toHaveTextContent("Sign-in was cancelled.");
});

test("signing in merges this browser's progress with the account's", async () => {
  localStorage.setItem("algolens.done", JSON.stringify(["kadane"]));
  mockApi({ enabled: true, user: USER }, ["merge-sort"]);
  renderAt("/account");
  expect(await screen.findByRole("link", { name: /your account \(ada learner\)/i })).toBeInTheDocument();
  await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
  const put = calls.find((c) => c.method === "PUT")!;
  expect(put.url).toBe("/api/me/progress");
  expect(put.headers["X-Requested-With"]).toBe("algolens");
  expect(new Set((put.body as { done: string[] }).done)).toEqual(new Set(["kadane", "merge-sort"]));
  expect(new Set(JSON.parse(localStorage.getItem("algolens.done")!))).toEqual(new Set(["kadane", "merge-sort"]));
  expect(await screen.findByText(/2 topics marked as done/)).toBeInTheDocument();
});

test("deleting the account asks first, then signs out", async () => {
  mockApi({ enabled: true, user: USER });
  const user = userEvent.setup();
  renderAt("/account");
  await user.click(await screen.findByRole("button", { name: /delete my account/i }));
  expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  await user.click(screen.getByRole("button", { name: /yes, delete everything/i }));
  expect(await screen.findByText(/continue without an account/i)).toBeInTheDocument();
  const del = calls.find((c) => c.method === "DELETE")!;
  expect(del.url).toBe("/api/auth/me");
  expect(del.headers["X-Requested-With"]).toBe("algolens");
});

test("sign up asks for a name and sends it with the code", async () => {
  mockApi({ enabled: true, user: null });
  const user = userEvent.setup();
  renderAt("/account?mode=login");
  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  expect(screen.queryByLabelText(/your name/i)).toBeNull();
  await user.click(screen.getByRole("button", { name: "Sign up", pressed: false }));
  expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign up with google/i })).toBeInTheDocument();
  await user.type(screen.getByLabelText(/your name/i), "Grace Hopper");
  await user.type(screen.getByLabelText(/your email/i), "new@example.com");
  await user.click(screen.getByRole("button", { name: /sign up with email/i }));
  await user.type(await screen.findByLabelText("Code"), "123456");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  await screen.findByRole("link", { name: /your account/i });
  const verify = calls.find((c) => c.url === "/api/auth/email/verify")!;
  expect(verify.body).toEqual({ email: "new@example.com", code: "123456", name: "Grace Hopper" });
});
