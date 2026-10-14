import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, type JobView } from "../api";
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
      <p className={styles.lead}>Writing solutions and checking each one usually takes a few minutes.</p>
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
        {job?.status === "failed" && (
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

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
