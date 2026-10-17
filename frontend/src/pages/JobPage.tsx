import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, type JobView } from "../api";
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

  useEffect(() => {
    let closed = false;
    let source: EventSource | null = null;
    let timer: number | undefined;

    const update = (view: JobView) => {
      if (closed) return;
      setJob(view);
      if (view.status === "done" && view.problem_id) {
        pasted.jobBecame(view.id, view.problem_id);
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
        .catch((e: Error) => !closed && setError(e.message));
    };

    if (typeof EventSource === "function") {
      source = new EventSource(api.jobEventsUrl(jobId));
      source.onmessage = (ev) => {
        const view = JSON.parse(ev.data) as JobView;
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
      <h1>Working on it</h1>
      <p className={styles.lead}>
        We're writing solutions and putting each one through its tests. It usually takes two to five minutes,
        so this is a good moment for a sip of water.
      </p>
      <div className={styles.progress} role="status" aria-live="polite">
        {!job && <p>Connecting…</p>}
        {job && job.status !== "failed" && (
          <>
            <p className={styles.stage}>{capitalize(job.stage || "starting")}</p>
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
        {job?.status === "failed" && !job.quota && (
          <div role="alert">
            <p>This problem couldn't be processed: {job.error || "an unknown error"}.</p>
            <p>
              Nothing was marked verified or wrong because of it. <Link to="/solve">Try again</Link>
            </p>
          </div>
        )}
      </div>
    </section>
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

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
