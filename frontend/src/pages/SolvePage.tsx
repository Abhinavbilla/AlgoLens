import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ApiError, OFFLINE_MESSAGE, api, type Allowance } from "../api";
import { pasted } from "./TryAgain";
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
  const [allowance, setAllowance] = useState<Allowance | null>(null);
  const [limitMessage, setLimitMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .allowance()
      .then((a) => !cancelled && setAllowance(a))
      .catch(() => {}); // only a hint: the server still checks on submit
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setLimitMessage("");
    try {
      const out = await api.submit(text);
      // The text stays only in this tab's memory; the server keeps a hash of it.
      if ("problem_id" in out) {
        pasted.forProblem(out.problem_id, text);
        navigate(`/problems/${out.problem_id}`);
      } else {
        pasted.forJob(out.job_id, text);
        navigate(`/jobs/${out.job_id}`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.detail?.kind === "daily_limit") {
        setLimitMessage(err.message);
        if (err.detail.allowance) setAllowance(err.detail.allowance as Allowance);
      } else {
        setError(err instanceof ApiError ? err.message : OFFLINE_MESSAGE);
      }
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
          {allowance && allowance.left !== null && !limitMessage && <AllowanceNote allowance={allowance} />}
          {limitMessage && allowance && <LimitCard message={limitMessage} allowance={allowance} />}
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

function localTime(iso: string | null) {
  if (!iso) return null;
  const at = new Date(iso);
  const time = at.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return at.toDateString() === new Date().toDateString() ? time : `${time} tomorrow`;
}

function AllowanceNote({ allowance: a }: { allowance: Allowance }) {
  if (a.left === null) return null;
  if (a.left > 0) {
    return (
      <p className={styles.allowance}>
        {a.left} of {a.limit} new problem{a.limit === 1 ? "" : "s"} left today. Only problems that are solved
        and verified count; if something goes wrong along the way, it doesn't.
      </p>
    );
  }
  const at = localTime(a.retry_at);
  return (
    <p className={styles.allowance}>
      {a.used >= a.limit
        ? `You've used today's ${a.limit} new problems${at ? `; the next one frees up around ${at}` : ""}. `
        : "Your problems still being solved use up today's limit. "}
      A problem that has been solved before still opens straight away.
    </p>
  );
}

// Shown after the server refused a new problem: the learner's own limit, not an error.
function LimitCard({ message, allowance: a }: { message: string; allowance: Allowance }) {
  const at = a.used >= a.limit ? localTime(a.retry_at) : null;
  return (
    <div className={styles.quota} role="alert">
      <p className={styles.quotaTitle}>
        {a.used >= a.limit ? "Today's limit is finished" : "Wait for your problems to finish"}
      </p>
      <p>{tidy(message)}</p>
      {at && (
        <p className={styles.quotaWhen}>
          You can paste a new one around <strong>{at}</strong> (your time).
        </p>
      )}
      <p>
        <Link to="/library">Explore the library</Link> · <Link to="/path">Learning path</Link>
      </p>
    </div>
  );
}

// The title already says it: "Today's limit is finished: you've solved…" → "You've solved…".
function tidy(message: string) {
  const rest = message.replace(/^Today's limit is finished: /, "");
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}
