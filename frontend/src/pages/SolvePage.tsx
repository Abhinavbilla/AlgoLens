import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api";
import styles from "./solve.module.css";

export const MAX_TEXT = 10_000;

// Written for this page, so a first-time visitor can see what a good paste looks like.
const EXAMPLE = `Longest Run of Ones
Given a binary array nums (every value is 0 or 1), return the length of the longest stretch of consecutive 1s.

Example 1: nums = [1,1,0,1,1,1] -> 3
Example 2: nums = [1,0,1,1,0,1] -> 2
Example 3: nums = [0,0] -> 0

Constraints: 1 <= nums.length <= 10^5, nums[i] is 0 or 1`;

const PLACEHOLDER =
  "Title\nWhat the input is and what to return…\n\nExample 1: nums = [2,7,11,15], target = 9 -> [0,1]";

export function SolvePage() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const out = await api.submit(text);
      // The text stays only in this tab's memory; the server keeps a hash of it.
      if ("problem_id" in out) navigate(`/problems/${out.problem_id}`);
      else navigate(`/jobs/${out.job_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the server.");
      setBusy(false);
    }
  }

  const tooLong = text.length > MAX_TEXT;
  return (
    <div className={styles.solveLayout}>
      <section className={styles.solve}>
        <p className={styles.eyebrow}>Your own problem</p>
        <h1 className={styles.solveTitle}>Paste a problem</h1>
        <p className={styles.lead}>
          Paste a problem statement with at least one worked example, the way you'd find it on a practice
          site. You'll get a brute force and better approaches, and every one is run before you see it.
        </p>
        <form onSubmit={onSubmit}>
          <div className={styles.labelRow}>
            <label htmlFor="statement" className={styles.label}>
              Problem statement
            </label>
            <button type="button" className={styles.linkButton} onClick={() => setText(EXAMPLE)}>
              Try an example
            </button>
          </div>
          <textarea
            id="statement"
            className={styles.textarea}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={14}
            spellCheck={false}
            placeholder={PLACEHOLDER}
            aria-describedby="statement-count statement-privacy"
            aria-invalid={tooLong}
          />
          <div className={styles.formFoot}>
            <span id="statement-count" className={tooLong ? styles.over : styles.muted}>
              {text.length.toLocaleString()} / {MAX_TEXT.toLocaleString()} characters
            </span>
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={busy || tooLong || text.trim().length < 20}
            >
              {busy ? "Sending…" : "Solve and verify"}
            </button>
          </div>
          <p id="statement-privacy" className={styles.muted}>
            The statement is sent to the configured AI service to be solved. AlgoLens itself doesn't store it:
            only a fingerprint, so the same problem isn't solved twice.
          </p>
          {error && (
            <p role="alert" className={styles.error}>
              {error}
            </p>
          )}
        </form>
      </section>

      <aside className={styles.how} aria-labelledby="how-h">
        <h2 id="how-h">What happens next</h2>
        <ol>
          <li>
            <strong>Read.</strong> The statement becomes a precise signature, input rules and the worked
            examples. Anything out of scope is turned down with a reason.
          </li>
          <li>
            <strong>Solve, twice over.</strong> Two brute forces are written independently, plus one or two
            faster approaches.
          </li>
          <li>
            <strong>Check.</strong> Every approach runs on the examples and hundreds of random inputs, and its
            C++ must match its Python. Failures get a chance to be fixed.
          </li>
          <li>
            <strong>Show.</strong> Only what passes is marked verified, with a step-by-step animation and a
            chart of how it scales.
          </li>
        </ol>
        <p className={styles.muted}>Usually takes two to five minutes.</p>
      </aside>
    </div>
  );
}
