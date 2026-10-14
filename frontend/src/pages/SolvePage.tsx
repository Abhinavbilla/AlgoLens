import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api";
import styles from "./solve.module.css";

export const MAX_TEXT = 10_000;

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
    <section className={styles.solve}>
      <h1>Paste a problem</h1>
      <p className={styles.lead}>
        Paste a full problem statement with at least one worked example. AlgoLens writes a brute force and
        better approaches, then checks every one by running it against the examples and 300 random inputs.
      </p>
      <form onSubmit={onSubmit}>
        <label htmlFor="statement" className={styles.label}>
          Problem statement
        </label>
        <textarea
          id="statement"
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={14}
          spellCheck={false}
          aria-describedby="statement-count statement-privacy"
          aria-invalid={tooLong}
        />
        <div className={styles.formFoot}>
          <span id="statement-count" className={tooLong ? styles.over : styles.muted}>
            {text.length.toLocaleString()} / {MAX_TEXT.toLocaleString()} characters
          </span>
          <button type="submit" disabled={busy || tooLong || text.trim().length < 20}>
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
  );
}
