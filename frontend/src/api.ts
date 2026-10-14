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
  | ArrayPanel
  | VarsPanel
  | MapPanel
  | SequencePanel
  | LinkedListPanel
  | TreePanel
  | GraphPanel
  | GridPanel;

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
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let issues: Issue[] = [];
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail && typeof body.detail.message === "string") {
        message = body.detail.message;
        issues = Array.isArray(body.detail.issues) ? body.detail.issues : [];
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(res.status, message, issues);
  }
  return res.json() as Promise<T>;
}

const get = <T,>(path: string) => request<T>(path);

// Pasted problems (backend/algolens/api/problems.py).

export type Submitted = { job_id: string } | { problem_id: string };

export type JobView = {
  id: string;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  tests_passed: number;
  tests_total: number;
  error: string;
  problem_id: string | null;
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
  submit: (text: string) =>
    request<Submitted>("/api/problems", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  job: (id: string) => get<JobView>(`/api/jobs/${encodeURIComponent(id)}`),
  jobEventsUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/events`,
  problem: (id: string) => get<ProblemView>(`/api/problems/${encodeURIComponent(id)}`),
  compare: (pid: string) => get<Comparison>(`/api/problems/${encodeURIComponent(pid)}/compare`),
  approachAnimation: (pid: string, aid: string) =>
    get<Animation>(`/api/problems/${encodeURIComponent(pid)}/approaches/${encodeURIComponent(aid)}/animation`),
  customApproachAnimation: (pid: string, aid: string, args: unknown[]) =>
    request<Animation>(
      `/api/problems/${encodeURIComponent(pid)}/approaches/${encodeURIComponent(aid)}/animation`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ args }) },
    ),
};
