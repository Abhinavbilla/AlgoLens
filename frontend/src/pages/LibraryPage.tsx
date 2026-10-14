import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api, type EntrySummary } from "../api";
import { VerificationBadge } from "../VerificationBadge";
import styles from "./pages.module.css";

export function LibraryPage() {
  const [entries, setEntries] = useState<EntrySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .library()
      .then((data) => !cancelled && setEntries(data))
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <h1>Algorithm library</h1>
      <p className={styles.summary}>Pick an algorithm to watch it run, one step at a time.</p>
      {error && <p role="alert">{error}</p>}
      {!entries && !error && <p role="status">Loading…</p>}
      {entries && (
        <ul className={styles.cards}>
          {entries.map((e) => (
            <li key={e.slug} className={styles.card}>
              <p className={styles.category}>{e.category}</p>
              <h2>
                <Link to={`/library/${e.slug}`}>{e.title}</Link>
              </h2>
              <p>{e.summary}</p>
              <VerificationBadge verification={e.verification} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
