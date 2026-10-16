import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, api, type Animation, type Entry } from "../api";
import { InputEditor } from "../input/InputEditor";
import { EntryExtras } from "../learn/EntryExtras";
import { InlineMarkdown } from "../InlineMarkdown";
import { TopicIcon } from "../TopicIcon";
import { sectionFor } from "./sections";
import { AnimationView } from "../player/AnimationView";
import { TutorProvider } from "../tutor/TutorContext";
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
        <Link to="/library">Back to the library</Link>
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
      document
        .getElementById("player")
        ?.scrollIntoView?.({ behavior: reduce ? "auto" : "smooth", block: "start" });
      return null;
    } catch (err) {
      if (err instanceof ApiError) return { message: err.message, issues: err.issues };
      return { message: "Couldn't reach the server.", issues: [] };
    } finally {
      setRunning(false);
    }
  }

  const tutor = {
    target: { kind: "library" as const, id: slug },
    title: e.title,
    functionName: e.entry,
    params: e.params.map((p) => p.name),
    suggestions: [
      "Why does this work?",
      "Walk me through the example input",
      "Where does the time complexity come from?",
      "What kinds of problems is this used for?",
    ],
  };

  return (
    <TutorProvider page={tutor}>
    <article className={styles.entry}>
      <header className={styles.entryHeader}>
        <p className={styles.crumbs}>
          <Link to="/library">Library</Link> /{" "}
          <Link to={`/topics/${sectionFor(e.category)}`}>{e.category}</Link>
        </p>
        <h1 className={styles.entryTitle}>
          <TopicIcon topic={sectionFor(e.category)} size={44} />
          <span>{e.title}</span>
        </h1>
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
        <h2>The idea</h2>
        {e.description.split(/\n\s*\n/).map((para, i) => (
          <p key={i}>
            <InlineMarkdown text={para} />
          </p>
        ))}
      </section>
      <EntryExtras slug={slug} />
    </article>
    </TutorProvider>
  );
}
