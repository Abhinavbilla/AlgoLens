import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api, type EntrySummary } from "../api";
import styles from "./home.module.css";
import { SECTIONS, sectionFor, type Section } from "./sections";
import { SortingPreview } from "./SortingPreview";

export function LibraryPage() {
  const [entries, setEntries] = useState<EntrySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

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

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const shown = (entries ?? []).filter(
      (e) => !q || `${e.title} ${e.summary} ${e.category}`.toLowerCase().includes(q),
    );
    const all: Section[] = [...SECTIONS, { id: "more", title: "More", intro: "", categories: [] }];
    return all
      .map((s) => ({ section: s, items: shown.filter((e) => sectionFor(e.category) === s.id) }))
      .filter((g) => g.items.length > 0);
  }, [entries, query]);

  const verified = entries?.filter((e) => e.verification.status === "verified").length ?? 0;

  return (
    <div className={styles.home}>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>Algorithms, step by step</p>
          <h1 id="hero-title" className={styles.heroTitle}>
            See what your code is <em>actually</em> doing.
          </h1>
          <p className={styles.heroLead}>
            Every animation here is a recording of real code running, never a drawing of what it should do.
            Each step comes with one plain sentence explaining it. Paste your own problem and get working
            solutions, each one tested before you see it.
          </p>
          <div className={styles.heroActions}>
            <a href="#library" className={styles.primary}>
              Browse the library
            </a>
            <Link to="/solve" className={styles.secondary}>
              Paste a problem →
            </Link>
          </div>
        </div>
        <SortingPreview />
      </section>

      <ul className={styles.points}>
        <li>
          <strong>Recorded, not drawn.</strong> We trace the program line by line. Step back and forward and
          you see exactly the same state.
        </li>
        <li>
          <strong>Tested before it's shown.</strong> Solutions run against the worked examples and hundreds of
          random inputs. Anything that fails is labelled, never passed off as right.
        </li>
        <li>
          <strong>Python and C++, side by side.</strong> The current line is highlighted in both, so you can
          read along in either language.
        </li>
      </ul>

      <section id="library" className={styles.library} aria-labelledby="library-title">
        <div className={styles.libraryHead}>
          <div>
            <h2 id="library-title" className={styles.sectionTitle}>
              Algorithm library
            </h2>
            <p className={styles.libraryMeta}>
              {entries
                ? `${entries.length} algorithms, ${verified} verified. All of them play offline.`
                : "Loading the library…"}
            </p>
          </div>
          <label className={styles.search}>
            <span className="sr-only">Search the library</span>
            <input
              type="search"
              placeholder="Search: “heap”, “tree”, “window”…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>

        {entries && !query && (
          <nav className={styles.jump} aria-label="Library sections">
            {groups.map((g) => (
              <a key={g.section.id} href={`#${g.section.id}`}>
                {g.section.title} <span>{g.items.length}</span>
              </a>
            ))}
          </nav>
        )}

        {error && <p role="alert">{error}</p>}
        {!entries && !error && <p role="status">Loading…</p>}
        {entries && groups.length === 0 && <p>Nothing matches “{query}”.</p>}

        {groups.map(({ section, items }) => (
          <section
            key={section.id}
            id={section.id}
            className={styles.group}
            aria-labelledby={`${section.id}-h`}
          >
            <header className={styles.groupHead}>
              <h3 id={`${section.id}-h`}>{section.title}</h3>
              {section.intro && <p>{section.intro}</p>}
            </header>
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
                      Watch →
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </section>
    </div>
  );
}
