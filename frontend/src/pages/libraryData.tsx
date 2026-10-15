import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api, type EntrySummary } from "../api";
import { TopicIcon } from "../TopicIcon";
import styles from "./home.module.css";
import { SECTIONS, sectionFor, type Section } from "./sections";

// Shared by the home page, the library index and each topic page.

export function useLibrary() {
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
  return { entries, error };
}

export const MORE: Section = {
  id: "more",
  title: "More",
  intro: "Everything else in the library.",
  categories: [],
};

export type Topic = { section: Section; items: EntrySummary[] };

/** Every topic that has at least one entry, in the library's order. */
export function useTopics(entries: EntrySummary[] | null): Topic[] {
  return useMemo(
    () =>
      [...SECTIONS, MORE]
        .map((section) => ({
          section,
          items: (entries ?? []).filter((e) => sectionFor(e.category) === section.id),
        }))
        .filter((t) => t.items.length > 0),
    [entries],
  );
}

export function TopicTiles({ topics }: { topics: Topic[] }) {
  return (
    <ul className={styles.tiles}>
      {topics.map(({ section, items }) => (
        <li key={section.id} className={styles.tile}>
          <span className={styles.tileIcon}>
            <TopicIcon topic={section.id} size={36} />
          </span>
          <Link to={`/topics/${section.id}`} className={styles.tileTitle}>
            {section.title}
          </Link>
          <span className={styles.tileIntro}>{section.intro}</span>
          <span className={styles.tileFoot}>
            <span>
              {items.length} algorithm{items.length === 1 ? "" : "s"}
            </span>
            <span className={styles.cardGo} aria-hidden="true">
              Explore →
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export function EntryCards({ items }: { items: EntrySummary[] }) {
  return (
    <ul className={styles.cards}>
      {items.map((e) => (
        <li key={e.slug} className={styles.card}>
          <span className={styles.cardCategory}>{e.category}</span>
          <Link to={`/library/${e.slug}`} className={styles.cardTitle}>
            {e.title}
          </Link>
          <span className={styles.cardSummary}>{e.summary}</span>
          <span className={styles.cardFoot}>
            {e.verification.status === "verified" ? (
              <span className={styles.cardVerified}>
                <span aria-hidden="true">✓</span> Verified · {e.verification.tests} tests
              </span>
            ) : (
              <span className={styles.cardUnverified}>Not verified yet</span>
            )}
            <span className={styles.cardGo} aria-hidden="true">
              Watch it run →
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
