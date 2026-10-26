// Shapes returned by the backend (backend/algolens/api/library.py, animation/builder.py).

export type Verification = {
  status: "verified" | "failed" | "unverified";
  checked_at?: string;
  method?: string;
  tests?: number;
  failures?: string[];
};

export type EntrySummary = {
  slug: string;
  title: string;
  category: string;
  summary: string;
  verification: Verification;
};

export type InputParam = { name: string; kind: string; hint: string };

export type Entry = EntrySummary & {
  entry: string; // the function's name
  description: string;
  note: string;
  python_code: string;
  cpp_code: string;
  default_input: { args: unknown[] };
  params: InputParam[];
};

export type Issue = { path: string; message: string };

export type Narration = { text: string; source: "template" | "neutral" };

export type StackEntry = { aid: number; fn: string; line: number; call: string; new: boolean };

export type ArrayPanel = {
  kind: "array";
  label: string;
  defined: boolean;
  items?: string[];
  changed?: number[];
  pointers?: { label: string; index: number }[];
  range?: { label: string; from: number; to: number };
};

export type VarsPanel = {
  kind: "vars";
  label: string;
  items: { name: string; defined: boolean; value?: string; changed?: boolean }[];
};

export type MapPanel = {
  kind: "map";
  label: string;
  defined: boolean;
  entries?: { key: string; value: string; changed: boolean }[];
};

export type SequencePanel = {
  kind: "stack" | "queue" | "list";
  label: string;
  defined: boolean;
  items?: string[];
  changed?: number[];
};

export type LinkedListPanel = {
  kind: "linked_list";
  label: string;
  defined: boolean;
  nodes?: { id: number; text: string }[];
  cycle_to?: number | null;
  pointers?: { label: string; node: number | null }[];
};

export type TreePanel = {
  kind: "tree";
  label: string;
  defined: boolean;
  nodes?: { id: number; text: string; x: number; y: number; marks: string[] }[];
  edges?: { from: number; to: number }[];
  pointers?: { label: string; node: number | null }[];
  width?: number;
  height?: number;
};

export type GraphPanel = {
  kind: "graph";
  label: string;
  defined: boolean;
  nodes?: { id: number; x: number; y: number; label: string | null; marks: string[] }[];
  edges?: { u: number; v: number; w: string | null }[];
  pointers?: { label: string; node: number }[];
  directed?: boolean;
};

export type GridCell = { text: string; marks: string[]; changed: boolean };

export type GridPanel = {
  kind: "grid";
  label: string;
  defined: boolean;
  rows?: GridCell[][];
  pointers?: { label: string; row: number; col: number }[];
  row_header?: string[];
  col_header?: string[];
};

export type Panel =
  ArrayPanel | VarsPanel | MapPanel | SequencePanel | LinkedListPanel | TreePanel | GraphPanel | GridPanel;

export type Frame = {
  i: number;
  line: number;
  next: number | "return" | null;
  cpp_line: number | null;
  code: string;
  ops: number;
  aid: number;
  stack: StackEntry[];
  panels: Panel[];
  narration: Narration;
  ret?: string;
  raised?: string;
};

export type Animation = {
  frames: Frame[];
  total_ops: number;
  result: unknown;
  input: { args: unknown[] };
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public issues: Issue[] = [],
    /** The server's structured detail, when it sent one (e.g. the daily allowance). */
    public detail: Record<string, unknown> | null = null,
  ) {
    super(message);
  }
}

// What to say when the server didn't explain an error itself (a proxy page, a crash).
const STATUS_MESSAGES: Record<number, string> = {
  400: "The server couldn't understand that request. Reload the page and try again.",
  404: "That wasn't found. It may have been removed; go back and try again.",
  408: "The server took too long to answer. Try again.",
  413: "That's too large to send. Try something shorter.",
  422: "Some of what was sent isn't valid. Check it and try again.",
  429: "Too many requests in a short time. Wait a minute and try again.",
  500: "Something went wrong on the AlgoLens server. Try again in a moment.",
  502: "The AlgoLens server isn't responding (it may be restarting). Try again in a minute.",
  503: "AlgoLens is temporarily unavailable (it may be restarting). Try again in a minute.",
  504: "The AlgoLens server took too long to answer. Try again in a minute.",
};

export const OFFLINE_MESSAGE =
  "Couldn't reach AlgoLens. Check your internet connection, then try again.";

export function statusMessage(status: number): string {
  return (
    STATUS_MESSAGES[status] ??
    (status >= 500
      ? STATUS_MESSAGES[500]
      : "Something went wrong with that request. Reload the page and try again.")
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, OFFLINE_MESSAGE);
  }
  if (!res.ok) {
    let message = statusMessage(res.status);
    let issues: Issue[] = [];
    let detail: Record<string, unknown> | null = null;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail && typeof body.detail.message === "string") {
        message = body.detail.message;
        issues = Array.isArray(body.detail.issues) ? body.detail.issues : [];
        detail = body.detail;
      }
      // A list detail is FastAPI's own validation dump: keep the plain status message.
    } catch {
      // not JSON (a proxy's error page): keep the plain status message
    }
    throw new ApiError(res.status, message, issues, detail);
  }
  return res.json() as Promise<T>;
}

const get = <T>(path: string) => request<T>(path);

// Pasted problems (backend/algolens/api/problems.py).

export type Submitted = { job_id: string } | { problem_id: string };

export type JobView = {
  id: string;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  tests_passed: number;
  tests_total: number;
  error: string;
  /** Why a failed job stopped (backend/algolens/failures.py). */
  error_kind?: string | null;
  problem_id: string | null;
  /** Set when the free AI allowance ran out: when it should be back, if the provider said. */
  quota?: { retry_at: string | null; daily: boolean } | null;
  /** While waiting: jobs ahead of this one and roughly how long until it starts. */
  queue?: { ahead: number; wait_s: number; typical_s: number } | null;
};

/** New problems this visitor can still have solved in 24 hours (left is null: no limit). */
export type Allowance = {
  limit: number;
  used: number;
  in_progress: number;
  left: number | null;
  retry_at: string | null;
};

export type ApproachView = {
  id: string;
  name: string;
  key_idea: string;
  time: string;
  space: string;
  python_code: string;
  cpp_code: string;
  status: "verified" | "unverified" | "timeout";
  is_brute: boolean;
  reason: string;
  tests_passed: number;
  tests_total: number;
  examples_checked: number;
  repairs: number;
  exhaustive?: boolean; // the tests covered every valid input
  limited?: boolean; // fewer than 300 random inputs could be made; tested on those
  examples_passed?: boolean; // not verified, but right on every worked example
  failing_case: Record<string, unknown> | null;
  animated: boolean;
  animation_note: string;
  default_input?: { args: unknown[] };
};

export type Comparison = {
  sizes: number[];
  series: { id: string; name: string; points: { n: number; ops: number | null; status: string }[] }[];
  limits: { cpu_ms: number };
};

export type ApproachThinking = {
  name: string;
  time: string;
  space: string;
  is_brute: boolean;
  intuition: string;
  bottleneck: string;
  data_structure: { name: string; why: string } | null;
  steps: string[];
  complexity_reasoning: string;
};

export type Explanation = {
  understanding: { restated: string; inputs_outputs: string; observations: string[]; edge_cases: string[] };
  approaches: ApproachThinking[];
  pattern: string;
  takeaway: string;
};

export type ProblemView = {
  id: string;
  status: "done" | "rejected" | "failed";
  reason: string;
  title: string;
  function_name: string;
  params: { name: string }[];
  examples: { args: unknown[]; expected: unknown }[];
  comparator: string;
  inputs: InputParam[];
  explanation?: Explanation | null;
  approaches: ApproachView[];
};

export const api = {
  library: () => get<EntrySummary[]>("/api/library"),
  entry: (slug: string) => get<Entry>(`/api/library/${encodeURIComponent(slug)}`),
  animation: (slug: string) => get<Animation>(`/api/library/${encodeURIComponent(slug)}/animation`),
  customAnimation: (slug: string, args: unknown[]) =>
    request<Animation>(`/api/library/${encodeURIComponent(slug)}/animation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
    }),
  submit: (text: string, retry = false) =>
    request<Submitted>("/api/problems", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(retry ? { text, retry } : { text }),
    }),
  allowance: () => get<Allowance>("/api/problems/allowance"),
  job: (id: string) => get<JobView>(`/api/jobs/${encodeURIComponent(id)}`),
  jobEventsUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/events`,
  problem: (id: string) => get<ProblemView>(`/api/problems/${encodeURIComponent(id)}`),
  compare: (pid: string) => get<Comparison>(`/api/problems/${encodeURIComponent(pid)}/compare`),
  approachAnimation: (pid: string, aid: string) =>
    get<Animation>(
      `/api/problems/${encodeURIComponent(pid)}/approaches/${encodeURIComponent(aid)}/animation`,
    ),
  customApproachAnimation: (pid: string, aid: string, args: unknown[]) =>
    request<Animation>(
      `/api/problems/${encodeURIComponent(pid)}/approaches/${encodeURIComponent(aid)}/animation`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ args }) },
    ),
  chat: (body: ChatRequest) =>
    request<{ reply: string }>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  checkCode: (context: TutorTarget, code: string) =>
    request<CheckResult>("/api/chat/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context, code }),
    }),
};

// The tutor chat (backend/algolens/api/chat.py). The conversation lives only in the browser.

export type TutorTarget = { kind: "library" | "problem"; id: string; approach_id?: string | null };

export type TutorStep = {
  index: number;
  line: number | null;
  narration: string;
  variables: Record<string, unknown>;
};

export type ChatMessage = { role: "user" | "assistant"; content: string };

export type ChatMode = "explain" | "hint" | "review";

export type ChatRequest = {
  context: TutorTarget & { step?: TutorStep | null };
  mode: ChatMode;
  messages: ChatMessage[];
};

export type CheckResult = {
  verdict: "passed" | "wrong" | "error" | "missing_function" | string;
  passed: number;
  total: number;
  message: string;
  failure: { input: unknown[]; expected: unknown; got: unknown; outcome: string; detail: string } | null;
};

// Optional Google sign-in (backend/algolens/api/auth.py). Changes carry X-Requested-With,
// which the server requires so other sites can't make them on a learner's behalf.

export type User = { id: string; email: string; name: string; picture: string };

export type MyProblem = { id: string; title: string; status: string; added_at: string };

const change = <T>(path: string, method: string, body?: unknown) =>
  request<T>(path, {
    method,
    headers: { "Content-Type": "application/json", "X-Requested-With": "algolens" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const accounts = {
  me: () => get<{ enabled: boolean; google: boolean; email: boolean; user: User | null }>("/api/auth/me"),
  emailStart: (email: string) => change<{ sent: boolean; minutes: number; dev?: boolean }>("/api/auth/email/start", "POST", { email }),
  emailVerify: (email: string, code: string, name = "") =>
    change<{ user: User; created: boolean }>("/api/auth/email/verify", "POST", { email, code, name }),
  signInUrl: (next: string) => `/api/auth/google/login?next=${encodeURIComponent(next)}`,
  signOut: () => change<{ user: null }>("/api/auth/logout", "POST"),
  deleteAccount: () => change<{ deleted: boolean }>("/api/auth/me", "DELETE"),
  progress: () => get<{ done: string[] }>("/api/me/progress"),
  saveProgress: (done: string[]) => change<{ done: string[] }>("/api/me/progress", "PUT", { done }),
  problems: () => get<MyProblem[]>("/api/me/problems"),
  rememberProblem: (id: string) => change<{ saved: boolean }>(`/api/me/problems/${encodeURIComponent(id)}`, "POST"),
  forgetProblem: (id: string) => change<{ saved: boolean }>(`/api/me/problems/${encodeURIComponent(id)}`, "DELETE"),
};
