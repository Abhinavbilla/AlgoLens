import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api, type EntrySummary } from "../api";
import { PATH } from "../learn/path";
import { TopicIcon } from "../TopicIcon";
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
          <p className={styles.eyebrow}>Data structures &amp; algorithms, made visible</p>
          <h1 id="hero-title" className={styles.heroTitle}>
            See what your code is{" "}
            <span className={styles.scribbled}>
              <em>actually</em>
              <svg viewBox="0 0 200 18" preserveAspectRatio="none" aria-hidden="true">
                <path d="M3 12 C 40 4, 90 3, 130 7 S 186 14, 197 6" />
              </svg>
            </span>{" "}
            doing.
          </h1>
          <p className={styles.heroLead}>
            Most tutorials draw a picture of an algorithm and hope it matches the code. We do it the other way
            round: we run real code and show you every step it takes, with one plain sentence about what just
            happened. Build the foundations here, then take on LeetCode and Codeforces knowing exactly what's
            going on.
          </p>
          <div className={styles.heroActions}>
            <Link to="/path" className={styles.primary}>
              Start from the beginning
            </Link>
            <a href="#library" className={styles.secondary}>
              Browse the library
            </a>
            <Link to="/solve" className={styles.textLink}>
              Or paste a problem →
            </Link>
          </div>
        </div>
        <div className={styles.heroArt}>
          <p className={styles.note} aria-hidden="true">
            real code,
            <br />
            really running
            <svg viewBox="0 0 80 60" className={styles.noteArrow}>
              <path d="M6 6 C 20 30, 40 44, 70 50" />
              <path d="M58 42 L71 50 L57 56" />
            </svg>
          </p>
          <SortingPreview />
        </div>
      </section>

      <ul className={styles.points}>
        <li>
          <TopicIcon topic="searching" />
          <div>
            <strong>It's the real thing.</strong> Every frame is a recording of code actually running. Step
            back and forward as often as you like: you'll always see exactly the same state.
          </div>
        </li>
        <li>
          <TopicIcon topic="foundations" />
          <div>
            <strong>Nothing wrong gets through.</strong> Every solution is run against its examples and
            hundreds of random inputs before you see it. If something fails, we say so.
          </div>
        </li>
        <li>
          <TopicIcon topic="recursion" />
          <div>
            <strong>You do, not just watch.</strong> Try your own inputs, guess the next step before it
            happens, and play with every data structure before you use it.
          </div>
        </li>
      </ul>

      <section className={styles.journey} aria-labelledby="journey-title">
        <div className={styles.journeyHead}>
          <p className={styles.eyebrow}>The learning path</p>
          <h2 id="journey-title" className={styles.sectionTitle}>
            From your first loop to graphs and DP
          </h2>
          <p>
            Twelve stages, each building on the last. Every stage opens with a hands-on primer, then lets you
            watch the algorithms run. When you reach the end, the problems on LeetCode and Codeforces will
            look a lot friendlier.
          </p>
        </div>
        <ol className={styles.journeySteps}>
          {PATH.map((stage, i) => (
            <li key={stage.title}>
              <span className={styles.journeyIcon}>
                <TopicIcon topic={stage.icon} size={34} />
                <span className={styles.journeyNum}>{i + 1}</span>
              </span>
              <span className={styles.journeyTitle}>{stage.title}</span>
              <span className={styles.journeyWhy}>{stage.why}</span>
            </li>
          ))}
        </ol>
        <Link to="/path" className={styles.primary}>
          Open the learning path
        </Link>
      </section>

      <section id="library" className={styles.library} aria-labelledby="library-title">
        <div className={styles.libraryHead}>
          <div>
            <p className={styles.eyebrow}>The library</p>
            <h2 id="library-title" className={styles.sectionTitle}>
              Algorithm library
            </h2>
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
        {entries && groups.length === 0 && <p>Nothing matches “{query}”. Try a shorter word.</p>}

        {groups.map(({ section, items }) => (
          <section
            key={section.id}
            id={section.id}
            className={styles.group}
            aria-labelledby={`${section.id}-h`}
          >
            <header className={styles.groupHead}>
              <div className={styles.groupTitle}>
                <TopicIcon topic={section.id} />
                <h3 id={`${section.id}-h`}>{section.title}</h3>
              </div>
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
                      Watch it run →
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
