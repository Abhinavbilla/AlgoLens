import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, api, type Animation, type Entry } from "../api";
import { InputEditor } from "../input/InputEditor";
import { InlineMarkdown } from "../InlineMarkdown";
import { AnimationView } from "../player/AnimationView";
import { VerificationBadge } from "../VerificationBadge";
import styles from "./pages.module.css";

type Load<T> = { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: T };

export function EntryPage() {
  const { slug = "" } = useParams();
  // Keyed by entry, so moving to another entry starts from a fresh "loading" state.
  return <EntryContent key={slug} slug={slug} />;
}

function EntryContent({ slug }: { slug: string }) {
  const [entry, setEntry] = useState<Load<Entry>>({ status: "loading" });
  const [animation, setAnimation] = useState<Load<Animation>>({ status: "loading" });
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .entry(slug)
      .then((data) => !cancelled && setEntry({ status: "ok", data }))
      .catch((e: Error) => !cancelled && setEntry({ status: "error", message: e.message }));
    api
      .animation(slug)
      .then((data) => !cancelled && setAnimation({ status: "ok", data }))
      .catch((e: Error) => !cancelled && setAnimation({ status: "error", message: e.message }));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (entry.status === "loading") return <p role="status">Loading…</p>;
  if (entry.status === "error") {
    return (
      <section>
        <p role="alert">{entry.message}</p>
        <Link to="/">Back to the library</Link>
      </section>
    );
  }
  const e = entry.data;
  const shown = animation.status === "ok" ? animation.data.input.args : e.default_input.args;

  async function run(args: unknown[]) {
    setRunning(true);
    try {
      const data = await api.customAnimation(slug, args);
      setAnimation({ status: "ok", data });
      // The editor is below the player; bring the new run into view.
      const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      document.getElementById("player")?.scrollIntoView?.({ behavior: reduce ? "auto" : "smooth", block: "start" });
      return null;
    } catch (err) {
      if (err instanceof ApiError) return { message: err.message, issues: err.issues };
      return { message: "Couldn't reach the server.", issues: [] };
    } finally {
      setRunning(false);
    }
  }

  return (
    <article className={styles.entry}>
      <header className={styles.entryHeader}>
        <p className={styles.crumbs}>
          <Link to="/">Library</Link> / {e.category}
        </p>
        <h1>{e.title}</h1>
        <VerificationBadge verification={e.verification} />
        <p className={styles.summary}>{e.summary}</p>
        <p className={styles.input}>
          Input: <code>{shown.map((a) => JSON.stringify(a)).join(", ")}</code>
          {e.note && <span> · {e.note}</span>}
        </p>
      </header>
      <div id="player">
        {animation.status === "loading" && <p role="status">Recording a run…</p>}
        {animation.status === "error" && <p role="alert">{animation.message}</p>}
        {animation.status === "ok" && (
          // Keyed by input: a new run starts the player from its first step.
          <AnimationView
            key={JSON.stringify(animation.data.input)}
            animation={animation.data}
            python={e.python_code}
            cpp={e.cpp_code}
          />
        )}
      </div>
      <InputEditor
        params={e.params}
        initial={shown}
        defaults={e.default_input.args}
        running={running}
        onRun={run}
      />
      <section className={styles.about}>
        <h2>How it works</h2>
        {e.description.split(/\n\s*\n/).map((para, i) => (
          <p key={i}>
            <InlineMarkdown text={para} />
          </p>
        ))}
      </section>
    </article>
  );
}
