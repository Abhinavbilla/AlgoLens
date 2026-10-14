import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api, type Animation, type Entry } from "../api";
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
          Input: <code>{e.default_input.args.map((a) => JSON.stringify(a)).join(", ")}</code>
          {e.note && <span> · {e.note}</span>}
        </p>
      </header>
      {animation.status === "loading" && <p role="status">Recording a run…</p>}
      {animation.status === "error" && <p role="alert">{animation.message}</p>}
      {animation.status === "ok" && <AnimationView animation={animation.data} python={e.python_code} cpp={e.cpp_code} />}
      <section className={styles.about}>
        <h2>How it works</h2>
        {e.description.split(/\n\s*\n/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </section>
    </article>
  );
}
