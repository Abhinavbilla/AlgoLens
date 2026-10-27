import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { api } from "../api";
import { linkFor, recent, useRecent, type Recent } from "./recent";
import styles from "./recent.module.css";

const LABEL: Record<Recent["status"], string> = {
  solving: "Solving…",
  ready: "Ready",
  failed: "Couldn't finish",
  rejected: "Not supported",
};

function when(at: number) {
  const minutes = Math.round((Date.now() - at) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(at).toLocaleDateString([], { day: "numeric", month: "short" });
}

/** The problems pasted in this browser, on the Paste page. */
export function RecentList() {
  const list = useRecent();
  if (list.length === 0) return null;
  return (
    <section className={styles.recent} aria-labelledby="recent-h">
      <h2 id="recent-h">Your recent problems</h2>
      <p className={styles.hint}>
        Saved in this browser, so you can leave and come back. Opening one again doesn&rsquo;t use today&rsquo;s
        allowance.
      </p>
      <ul>
        {list.map((r) => (
          <li key={`${r.at}-${r.jobId ?? r.problemId}`}>
            <Link to={linkFor(r)} className={styles.title}>
              {r.title}
            </Link>
            <span className={`${styles.status} ${styles[r.status]}`}>{LABEL[r.status]}</span>
            <span className={styles.when}>{when(r.at)}</span>
            <button
              type="button"
              className={styles.remove}
              onClick={() => recent.remove(r)}
              aria-label={`Remove ${r.title} from this list`}
              title="Remove from this list"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

const POLL_MS = 5000;

/** On every page: follows a problem that's still being solved, then says when it's ready. */
export function SolvingPill() {
  const list = useRecent();
  const { pathname } = useLocation();
  const solving = list.filter((r) => r.status === "solving" && r.jobId);
  const [day] = useState(() => Date.now() - 24 * 3600 * 1000); // older outcomes aren't news
  const finished = list.find((r) => r.status !== "solving" && !r.seen && r.at > day);
  const shown = solving[0] ?? finished;
  const ids = solving.map((r) => r.jobId).join(",");

  // Poll the waiting jobs (the job page has its own live updates, so skip the one on screen).
  useEffect(() => {
    if (!ids) return;
    let stopped = false;
    const check = () => {
      for (const jobId of ids.split(",")) {
        if (pathname === `/jobs/${jobId}`) continue;
        api
          .job(jobId)
          .then((view) => {
            if (stopped) return;
            if (view.status === "done" && view.problem_id) recent.finished(jobId, view.problem_id);
            else if (view.status === "failed") recent.failed(jobId);
          })
          .catch(() => !stopped && recent.failed(jobId)); // gone (e.g. after a reset)
      }
    };
    check();
    const timer = window.setInterval(check, POLL_MS);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [ids, pathname]);

  if (!shown) return null;
  const link = linkFor(shown);
  if (pathname === link || (shown.jobId && pathname === `/jobs/${shown.jobId}`)) return null;

  const dismiss = () => (shown.jobId ? recent.seen(shown.jobId) : recent.opened(shown.problemId!, shown.title, "done"));
  return (
    <div className={`${styles.pill} ${styles[shown.status]}`} role="status" aria-live="polite">
      {shown.status === "solving" && <span className={styles.spinner} aria-hidden="true" />}
      <span className={styles.pillText}>
        {shown.status === "solving" && <>Solving &ldquo;{shown.title}&rdquo;</>}
        {shown.status === "ready" && <>&ldquo;{shown.title}&rdquo; is ready</>}
        {shown.status === "failed" && <>&ldquo;{shown.title}&rdquo; couldn&rsquo;t finish</>}
        {shown.status === "rejected" && <>&ldquo;{shown.title}&rdquo; isn&rsquo;t supported</>}
      </span>
      <Link to={link} className={styles.pillLink} onClick={() => shown.status !== "solving" && dismiss()}>
        {shown.status === "solving" ? "View progress" : shown.status === "ready" ? "Open" : "See why"}
      </Link>
      {shown.status !== "solving" && (
        <button type="button" className={styles.pillClose} onClick={dismiss} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}
