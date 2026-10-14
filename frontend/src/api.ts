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

export type Entry = EntrySummary & {
  description: string;
  note: string;
  python_code: string;
  cpp_code: string;
  default_input: { args: unknown[] };
};

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

export type Panel = ArrayPanel | VarsPanel | MapPanel;

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
  ) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // keep the generic message
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  library: () => get<EntrySummary[]>("/api/library"),
  entry: (slug: string) => get<Entry>(`/api/library/${encodeURIComponent(slug)}`),
  animation: (slug: string) => get<Animation>(`/api/library/${encodeURIComponent(slug)}/animation`),
};
