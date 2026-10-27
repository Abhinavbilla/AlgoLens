import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { ApiError, api } from "../api";
import { recent } from "./recent";
import styles from "./solve.module.css";

// The server keeps only a hash of a pasted statement, never the text. So "Try again" uses the
// copy kept in this browser tab, linked first to the job and then to the problem it became.

const KEY = "algolens:pasted:";

function save(key: string, text: string) {
  try {
    sessionStorage.setItem(KEY + key, text);
  } catch {
    // storage blocked: the learner can still paste it again
  }
}

function load(key: string): string | null {
  try {
    return sessionStorage.getItem(KEY + key);
  } catch {
    return null;
  }
}

export const pasted = {
  /** A job started for this text: keep the text for "Try again", and list it as recent. */
  forJob: (jobId: string, text: string) => {
    save(`job:${jobId}`, text);
    recent.started(jobId, text);
  },
  forProblem: (problemId: string, text: string) => save(`problem:${problemId}`, text),
  /** The job finished as this problem: keep the text with the problem. */
  jobBecame: (jobId: string, problemId: string) => {
    const text = load(`job:${jobId}`);
    if (text) save(`problem:${problemId}`, text);
  },
  textFor: (problemId: string) => load(`problem:${problemId}`),
  textForJob: (jobId: string) => load(`job:${jobId}`),
};

/** Solve the problem again, for results that aren't fully verified. */
export function TryAgain({ problemId }: { problemId: string }) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const text = pasted.textFor(problemId);

  if (!text) {
    return (
      <p className={styles.retry}>
        AI-written code can come out differently each time.{" "}
        <Link to="/solve">Paste the problem again</Link> and choose Try again to have another go.
      </p>
    );
  }

  async function retry() {
    setBusy(true);
    setError("");
    try {
      const out = await api.submit(text!, true);
      if ("job_id" in out) {
        pasted.forJob(out.job_id, text!);
        navigate(`/jobs/${out.job_id}`);
      } else {
        navigate(`/problems/${out.problem_id}`);
        setBusy(false);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the server.");
      setBusy(false);
    }
  }

  return (
    <div className={styles.retry}>
      <button type="button" className={styles.retryButton} onClick={retry} disabled={busy}>
        {busy ? "Starting…" : "↻ Try again"}
      </button>
      <span>AI-written code can come out differently each time. A new attempt uses some of today&rsquo;s AI allowance.</span>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
