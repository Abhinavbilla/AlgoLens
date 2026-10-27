import { useSyncExternalStore } from "react";

// The problems this browser pasted, newest first, so a result is never lost by wandering off
// to the library: the Paste page lists them, and a pill on every page follows one that's
// still being solved. Kept in this browser only, and only a title and a link: never the
// statement (the server doesn't keep it either; see TryAgain.tsx for the tab-only copy).

export type RecentStatus = "solving" | "ready" | "failed" | "rejected";

export type Recent = {
  jobId: string | null;
  problemId: string | null;
  title: string;
  status: RecentStatus;
  at: number; // when it was pasted (ms)
  seen: boolean; // the learner has looked at the outcome
};

const KEY = "algolens:recent";
const MAX = 20;
const EVENT = "algolens:recent";

// Snapshots must stay the same object until the stored list changes (useSyncExternalStore),
// so the parsed list is reused while the stored text is the same.
let lastRaw: string | null = null;
let cache: Recent[] = [];

function all(): Recent[] {
  let raw: string | null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    return cache; // storage blocked: whatever this page has kept
  }
  if (raw !== lastRaw) {
    lastRaw = raw;
    try {
      const parsed = JSON.parse(raw ?? "[]");
      cache = Array.isArray(parsed) ? (parsed as Recent[]) : [];
    } catch {
      cache = [];
    }
  }
  return cache;
}

function write(list: Recent[]) {
  cache = list.slice(0, MAX);
  try {
    lastRaw = JSON.stringify(cache);
    localStorage.setItem(KEY, lastRaw);
  } catch {
    // storage blocked: the list lasts until the page is reloaded
  }
  window.dispatchEvent(new Event(EVENT));
}

function update(match: (r: Recent) => boolean, change: Partial<Recent>) {
  write(all().map((r) => (match(r) ? { ...r, ...change } : r)));
}

/** A short name for a pasted statement: its first line. */
export function titleOf(text: string): string {
  const line = text.split("\n").find((l) => l.trim()) ?? "Your problem";
  const t = line.trim().replace(/\s+/g, " ");
  return t.length > 70 ? `${t.slice(0, 67)}…` : t;
}

export const recent = {
  list: all,

  /** Pasted and queued: follow it until it finishes. */
  started(jobId: string, text: string) {
    const rest = all().filter((r) => r.jobId !== jobId);
    write([
      { jobId, problemId: null, title: titleOf(text), status: "solving", at: Date.now(), seen: false },
      ...rest,
    ]);
  },

  /** The job finished as this problem. */
  finished(jobId: string, problemId: string) {
    const known = all().some((r) => r.jobId === jobId);
    if (known) update((r) => r.jobId === jobId, { problemId, status: "ready" });
  },

  failed(jobId: string) {
    update((r) => r.jobId === jobId && r.status === "solving", { status: "failed" });
  },

  /** A result was opened (straight from the cache, or after solving): remember it, seen. */
  opened(problemId: string, title: string, status: "done" | "rejected" | "failed", text?: string) {
    const outcome: RecentStatus = status === "done" ? "ready" : status === "rejected" ? "rejected" : "failed";
    const existing = all().find((r) => r.problemId === problemId);
    if (existing) {
      update((r) => r.problemId === problemId, { title: title || existing.title, status: outcome, seen: true });
    } else {
      const name = title || (text ? titleOf(text) : "Your problem");
      write([
        { jobId: null, problemId, title: name, status: outcome, at: Date.now(), seen: true },
        ...all(),
      ]);
    }
  },

  /** The learner saw how a job ended (on its own page). */
  seen(jobId: string) {
    update((r) => r.jobId === jobId, { seen: true });
  },

  remove(entry: Recent) {
    write(all().filter((r) => r !== entry && !(r.at === entry.at && r.title === entry.title)));
  },
};

function subscribe(onChange: () => void) {
  const fromOtherTab = (e: StorageEvent) => {
    if (e.key === KEY) onChange(); // all() notices the stored text changed
  };
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", fromOtherTab);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", fromOtherTab);
  };
}

export function useRecent(): Recent[] {
  return useSyncExternalStore(subscribe, all, () => []);
}

/** Where an entry leads: its result, or the job's progress (or reason it stopped). */
export function linkFor(r: Recent): string {
  if (r.problemId) return `/problems/${r.problemId}`;
  return `/jobs/${r.jobId}`;
}
