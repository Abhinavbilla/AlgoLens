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
};
