import { useCallback, useEffect, useState } from "react";

// What a learner has marked as done, kept in this browser only (there are no accounts).
// Keys are library slugs and primer ids ("primer:arrays").

const KEY = "algolens.done";
const EVENT = "algolens-progress";

function read(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    const list = raw ? (JSON.parse(raw) as unknown) : [];
    return new Set(Array.isArray(list) ? list.filter((x): x is string => typeof x === "string") : []);
  } catch {
    return new Set();
  }
}

function write(done: Set<string>) {
  try {
    localStorage.setItem(KEY, JSON.stringify([...done]));
  } catch {
    // Storage unavailable (private window): progress lasts for this visit only.
  }
  window.dispatchEvent(new Event(EVENT));
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
