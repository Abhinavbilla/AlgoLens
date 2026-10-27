import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError, OFFLINE_MESSAGE, api, type JobView } from "../api";
import { pickQuote, type Quote } from "./quotes";
import { recent } from "./recent";
import { pasted } from "./TryAgain";
import styles from "./solve.module.css";

export function JobPage() {
  const { jobId = "" } = useParams();
  return <JobProgress key={jobId} jobId={jobId} />;
}

function JobProgress({ jobId }: { jobId: string }) {
  const navigate = useNavigate();
  const [job, setJob] = useState<JobView | null>(null);
  const [error, setError] = useState("");
  const [quote] = useState(() => pickQuote()); // one per run, kept while this page is open

  useEffect(() => {
    let closed = false;
    let source: EventSource | null = null;
    let timer: number | undefined;

    const update = (view: JobView) => {
      if (closed) return;
      setJob(view);
      if (view.status === "failed") {
        recent.failed(view.id);
        recent.seen(view.id); // they're looking at why
      }
      if (view.status === "done" && view.problem_id) {
        pasted.jobBecame(view.id, view.problem_id);
        recent.finished(view.id, view.problem_id);
        navigate(`/problems/${view.problem_id}`, { replace: true });
      }
    };
    const final = (view: JobView) => view.status === "done" || view.status === "failed";

    // Polling is the fallback when the event stream isn't available.
    const poll = () => {
      api
        .job(jobId)
        .then((view) => {
          update(view);
          if (!final(view) && !closed) timer = window.setTimeout(poll, 2000);
        })
        .catch((e: Error) => {
          if (closed) return;
          setError(e.message);
          recent.failed(jobId); // e.g. a job from before a reset: stop following it
        });
    };

    if (typeof EventSource === "function") {
      source = new EventSource(api.jobEventsUrl(jobId));
      source.onmessage = (ev) => {
        let view: JobView;
        try {
          view = JSON.parse(ev.data) as JobView;
        } catch {
          return; // a garbled event: the next one (or polling) brings the state
        }
        update(view);
        if (final(view)) source?.close();
      };
      source.onerror = () => {
        source?.close();
        source = null;
        if (!closed) poll();
      };
    } else {
      poll();
    }
    return () => {
      closed = true;
      source?.close();
      window.clearTimeout(timer);
    };
  }, [jobId, navigate]);

  if (error) {
    return (
      <section className={styles.solve}>
        <p role="alert">{error}</p>
        <Link to="/solve">Paste a problem</Link>
      </section>
    );
  }
  const counting = job && job.tests_total > 0;
  return (
    <section className={styles.solve}>
      {job?.status === "failed" ? (
        <h1>This problem couldn't be finished</h1>
      ) : (
        <>
          <h1>Working on it</h1>
          <p className={styles.lead}>
            We're writing solutions and putting each one through its tests. It usually takes two to five minutes.
          </p>
          <QuoteCard quote={quote} />
        </>
      )}
      <div className={styles.progress} role="status" aria-live="polite">
        {!job && <p>Connecting…</p>}
        {job && job.status !== "failed" && (
          <>
            <p className={styles.stage}>{capitalize(job.stage || "starting")}</p>
            {job.queue && <QueueNote queue={job.queue} />}
            {/* Always rendered, so the layout doesn't jump when counting starts. */}
            <progress
              className={styles.bar}
              max={counting ? job.tests_total : 1}
              value={counting ? job.tests_passed : undefined}
              aria-label="Progress of the current check"
            />
            <p className={styles.muted}>
              {counting ? `${job.tests_passed} of ${job.tests_total} tests run` : " "}
            </p>
          </>
        )}
        {job?.status === "failed" && job.quota && <QuotaCard job={job} />}
        {job?.status === "failed" && !job.quota && <FailureCard job={job} />}
      </div>
    </section>
  );
}

// Titles for backend/algolens/failures.py's kinds; the message itself comes from the server.
const FAILURE_TITLES: Record<string, string> = {
  ai_setup: "AlgoLens can't use its AI service right now",
  ai_down: "The AI service isn't responding",
  ai_format: "The AI's answers came back unusable",
  too_big: "This statement is too long for the AI service",
  sandbox: "The code runner is down",
  lost_text: "Your statement was lost before work started",
  interrupted: "The server restarted while solving this",
  internal: "Something broke on our side",
};

// No point offering a retry while the server itself is misconfigured.
const NO_RETRY = new Set(["ai_setup"]);

function FailureCard({ job }: { job: JobView }) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [retryError, setRetryError] = useState("");
  const kind = job.error_kind ?? "";
  const text = pasted.textForJob(job.id);
  const canRetry = !!text && !NO_RETRY.has(kind);

  async function retry() {
    setBusy(true);
    setRetryError("");
    try {
      const out = await api.submit(text!);
      if ("job_id" in out) {
        pasted.forJob(out.job_id, text!);
        navigate(`/jobs/${out.job_id}`);
      } else {
        pasted.forProblem(out.problem_id, text!);
        navigate(`/problems/${out.problem_id}`);
      }
    } catch (e) {
      setRetryError(e instanceof ApiError ? e.message : OFFLINE_MESSAGE);
      setBusy(false);
    }
  }

  return (
    <div className={styles.quota} role="alert">
      <p className={styles.quotaTitle}>{FAILURE_TITLES[kind] ?? "This problem couldn't be processed"}</p>
      <p>{job.error || "The server didn't say what went wrong. Nothing was marked right or wrong because of it."}</p>
      {canRetry && (
        <p>
          <button type="button" className={styles.retryButton} onClick={retry} disabled={busy}>
            {busy ? "Starting…" : "↻ Try again"}
          </button>
        </p>
      )}
      {retryError && <p>{retryError}</p>}
      <p>
        <Link to="/solve">{canRetry ? "Paste a different problem" : "Paste it again"}</Link> ·{" "}
        <Link to="/library">Explore the library</Link>
      </p>
    </div>
  );
}

// The free AI allowance ran out: not a problem with the statement, so say when to come back.
function QuotaCard({ job }: { job: JobView }) {
  const at = job.quota?.retry_at ? new Date(job.quota.retry_at) : null;
  const local = at?.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const tomorrow = at && at.toDateString() !== new Date().toDateString();
  return (
    <div className={styles.quota} role="alert">
      <p className={styles.quotaTitle}>
        {job.quota?.daily ? "Today's free AI allowance is used up" : "The free AI service is at its limit"}
      </p>
      <p>{job.error}</p>
      {local && (
        <p className={styles.quotaWhen}>
          Back around <strong>{local}</strong>
          {tomorrow ? " tomorrow" : ""} (your time).
        </p>
      )}
      <p>
        <Link to="/library">Explore the library</Link> · <Link to="/path">Learning path</Link> ·{" "}
        <Link to="/solve">Paste it again later</Link>
      </p>
    </div>
  );
}

function QuoteCard({ quote }: { quote: Quote }) {
  return (
    <figure className={styles.quoteCard}>
      <span className={styles.quoteMark} aria-hidden="true">
        &ldquo;
      </span>
      <blockquote className={styles.quoteText}>{quote.text}</blockquote>
      <figcaption className={styles.quoteBy}>
        <span className={styles.quoteAuthor}>{quote.author}</span>
        <span className={styles.quoteSource}>{quote.source}</span>
      </figcaption>
    </figure>
  );
}

function QueueNote({ queue }: { queue: NonNullable<JobView["queue"]> }) {
  if (queue.ahead === 0) return <p className={styles.muted}>You're next: it starts in a moment.</p>;
  return (
    <p className={styles.queueNote}>
      {queue.ahead === 1 ? "1 problem is" : `${queue.ahead} problems are`} ahead of yours. Yours should start in
      about <strong>{minutes(queue.wait_s)}</strong>, then take around {minutes(queue.typical_s)}. You can leave
      this tab open and come back.
    </p>
  );
}

export function minutes(seconds: number) {
  const m = Math.max(1, Math.round(seconds / 60));
  if (m < 60) return `${m} minute${m === 1 ? "" : "s"}`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest ? `${h} h ${rest} min` : `${h} h`;
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
