import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api, type EntrySummary } from "../api";
import { TopicIcon } from "../TopicIcon";
import { PATH, PRIMERS } from "./path";
import styles from "./learn.module.css";
import { useProgress } from "./progress";

type Item = { id: string; title: string; summary: string; href: string; kind: "primer" | "algorithm" };

export function PathPage() {
  const [entries, setEntries] = useState<EntrySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { done, toggle } = useProgress();

  useEffect(() => {
    let cancelled = false;
    api
      .library()
      .then((data) => !cancelled && setEntries(data))
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const stages = useMemo(() => {
    const bySlug = new Map((entries ?? []).map((e) => [e.slug, e]));
    return PATH.map((stage) => ({
      ...stage,
      items: stage.items
        .map((id): Item | null => {
          if (id.startsWith("primer:")) {
            const key = id.slice("primer:".length);
            const p = PRIMERS[key];
            return p
              ? { id, title: p.title, summary: p.summary, href: `/learn/${key}`, kind: "primer" }
              : null;
          }
          const e = bySlug.get(id);
          return e
            ? { id, title: e.title, summary: e.summary, href: `/library/${id}`, kind: "algorithm" }
            : null;
        })
        .filter((x): x is Item => x !== null),
    })).filter((s) => s.items.length > 0);
  }, [entries]);

  const all = stages.flatMap((s) => s.items);
  const next = all.find((i) => !done.has(i.id));
  const finished = all.filter((i) => done.has(i.id)).length;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Learning path</p>
        <h1>Every DSA foundation, one picture at a time</h1>
        <p className={styles.lead}>
          The building blocks of data structures and algorithms, in the order that makes sense when you're
          starting out. Each step builds on the one before: see it run, try your own input, test yourself with{" "}
          <em>Predict the next step</em>, and mark it done. Then take on the matching problems on LeetCode or
          Codeforces, linked from every algorithm.
        </p>
        {entries && (
          <div className={styles.progress}>
            <div
              className={styles.bar}
              role="progressbar"
              aria-label="Path progress"
              aria-valuemin={0}
              aria-valuemax={all.length}
              aria-valuenow={finished}
            >
              <span style={{ width: `${all.length ? (100 * finished) / all.length : 0}%` }} />
            </div>
            <p>
              {finished} of {all.length} done
              {next && (
                <>
                  {" "}
                  · Next up: <Link to={next.href}>{next.title}</Link>
                </>
              )}
              {!next &&
                all.length > 0 &&
                " · You've finished the path. The foundations are yours: on to LeetCode and Codeforces!"}
            </p>
          </div>
        )}
      </header>

      {error && <p role="alert">{error}</p>}
      {!entries && !error && <p role="status">Loading…</p>}

      <ol className={styles.stages}>
        {stages.map((stage, n) => (
          <li key={stage.title} className={styles.stage}>
            <div className={styles.stageNum} aria-hidden="true">
              {n + 1}
            </div>
            <div className={styles.stageBody}>
              <h2 className={styles.stageTitle}>
                <TopicIcon topic={stage.icon} size={30} />
                {stage.title}
              </h2>
              <p className={styles.why}>{stage.why}</p>
              <ul className={styles.items}>
                {stage.items.map((item) => {
                  const isDone = done.has(item.id);
                  return (
                    <li key={item.id} className={isDone ? styles.itemDone : styles.item}>
                      <button
                        type="button"
                        className={styles.tick}
                        aria-pressed={isDone}
                        aria-label={`${item.title}: ${isDone ? "done" : "not done"}`}
                        onClick={() => toggle(item.id)}
                      >
                        <span aria-hidden="true">{isDone ? "✓" : ""}</span>
                      </button>
                      <div>
                        <Link to={item.href} className={styles.itemTitle}>
                          {item.title}
                        </Link>
                        {item.kind === "primer" && <span className={styles.tag}>primer</span>}
                        {next?.id === item.id && <span className={styles.nextTag}>next up</span>}
                        <p>{item.summary}</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
