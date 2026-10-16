import { useCallback, useEffect, useState } from "react";

// What a learner has marked as done, kept in this browser. Signed-in learners also get it
// saved to their account (account/AuthContext.tsx), so it follows them across devices.
// Keys are library slugs and primer ids ("primer:arrays").

const KEY = "algolens.done";
export const PROGRESS_EVENT = "algolens-progress";
const EVENT = PROGRESS_EVENT;

export function read(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    const list = raw ? (JSON.parse(raw) as unknown) : [];
    return new Set(Array.isArray(list) ? list.filter((x): x is string => typeof x === "string") : []);
  } catch {
    return new Set();
  }
}

/** `fromAccount`: the change came from the account, so it needn't be saved back to it. */
export function write(done: Set<string>, fromAccount = false) {
  try {
    localStorage.setItem(KEY, JSON.stringify([...done]));
  } catch {
    // Storage unavailable (private window): progress lasts for this visit only.
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { fromAccount } }));
}

export function useProgress() {
  const [done, setDone] = useState<Set<string>>(read);

  useEffect(() => {
    const sync = () => setDone(read());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const toggle = useCallback((id: string) => {
    const next = read();
    if (next.has(id)) next.delete(id);
    else next.add(id);
    write(next);
    setDone(next);
  }, []);

  return { done, toggle };
}
