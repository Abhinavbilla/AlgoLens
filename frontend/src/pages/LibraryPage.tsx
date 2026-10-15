import { useMemo, useState } from "react";
import styles from "./home.module.css";
import { EntryCards, TopicTiles, useLibrary, useTopics } from "./libraryData";

// The library's front door: every topic as a tile, plus a search across all algorithms.
export function LibraryPage() {
  const { entries, error } = useLibrary();
  const topics = useTopics(entries);
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const matches = useMemo(
    () => (entries ?? []).filter((e) => `${e.title} ${e.summary} ${e.category}`.toLowerCase().includes(q)),
    [entries, q],
  );
  const verified = entries?.filter((e) => e.verification.status === "verified").length ?? 0;

  return (
    <div className={styles.page}>
      <header className={styles.libraryHead}>
        <div>
          <p className={styles.eyebrow}>The library</p>
          <h1 className={styles.pageTitle}>Algorithm library</h1>
          <p className={styles.libraryMeta}>
            {entries
              ? `${entries.length} algorithms, ${verified} verified against hundreds of tests each. All of them work offline.`
              : "Loading the library…"}
          </p>
        </div>
        <label className={styles.search}>
          <span className="sr-only">Search the library</span>
          <input
            type="search"
            placeholder="Search: heap, tree, sliding window…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </header>

      {error && <p role="alert">{error}</p>}
      {!entries && !error && <p role="status">Loading…</p>}

      {entries && q && (
        <section aria-labelledby="results-h" className={styles.results}>
          <h2 id="results-h" className={styles.resultsTitle}>
            {matches.length === 0
              ? `Nothing matches “${query.trim()}”. Try a shorter word.`
              : `${matches.length} algorithm${matches.length === 1 ? "" : "s"} matching “${query.trim()}”`}
          </h2>
          <EntryCards items={matches} />
        </section>
      )}

      {entries && !q && <TopicTiles topics={topics} />}
    </div>
  );
}
