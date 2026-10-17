import { Link } from "react-router";
import { PATH } from "../learn/path";
import { TopicIcon } from "../TopicIcon";
import styles from "./home.module.css";
import { TopicTiles, useLibrary, useTopics } from "./libraryData";
import { SortingPreview } from "./SortingPreview";

export function HomePage() {
  const { entries, error } = useLibrary();
  const topics = useTopics(entries);

  return (
    <div className={styles.home}>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>DSA for complete beginners</p>
          <h1 id="hero-title" className={styles.heroTitle}>
            Start from zero. Solve LeetCode and Codeforces problems{" "}
            <span className={styles.scribbled}>
              <em>on your own.</em>
              <svg viewBox="0 0 200 18" preserveAspectRatio="none" aria-hidden="true">
                <path d="M3 12 C 40 4, 90 3, 130 7 S 186 14, 197 6" />
              </svg>
            </span>
          </h1>
          <p className={styles.heroLead}>
            Never written a linked list? Not sure what O(n) means? That&rsquo;s exactly where this starts. You
            watch real code run one step at a time, in plain words, and learn how to think a problem through:
            the obvious way first, then the fast one. Not a cram course for interviews, but the foundations that
            let you open a random problem and know where to begin.
          </p>
          <div className={styles.heroActions}>
            <Link to="/path" className={styles.primary}>
              Start learning, it&rsquo;s free
            </Link>
            <Link to="/library" className={styles.secondary}>
              I know some basics
            </Link>
          </div>
          <ul className={styles.badges} aria-label="What to expect">
            <li>Free</li>
            <li>No sign-up needed</li>
            <li>No experience needed</li>
            <li>Python &amp; C++</li>
          </ul>
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

      <section className={styles.climb} aria-labelledby="climb-title">
        <p className={styles.eyebrow}>How you&rsquo;ll get there</p>
        <h2 id="climb-title" className={styles.sectionTitle}>
          From &ldquo;where do I even start?&rdquo; to &ldquo;I can solve this&rdquo;
        </h2>
        <ol className={styles.climbSteps}>
          <li>
            <span className={styles.climbNum}>1</span>
            <strong>Start with nothing</strong>
            <span>
              Arrays, loops and Big-O, explained with pictures you can poke. Every idea is built from the one
              before it.
            </span>
          </li>
          <li>
            <span className={styles.climbNum}>2</span>
            <strong>Watch it, then try it</strong>
            <span>
              Step through each algorithm, guess the next move before it happens, and run it on your own
              inputs until it clicks.
            </span>
          </li>
          <li>
            <span className={styles.climbNum}>3</span>
            <strong>Solve problems yourself</strong>
            <span>
              Each topic ends with hand-picked LeetCode problems, Easy first, then Medium. After that,
              Codeforces&rsquo; beginner rounds (Div. 3 and Div. 4) are your next step. Stuck? Paste the problem
              and see it solved, step by step.
            </span>
          </li>
        </ol>
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

      <section className={styles.library} aria-labelledby="topics-title">
        <div className={styles.libraryHead}>
          <div>
            <p className={styles.eyebrow}>The library</p>
            <h2 id="topics-title" className={styles.sectionTitle}>
              Explore by topic
            </h2>
            <p className={styles.libraryMeta}>
              {entries
                ? `${entries.length} algorithms in ${topics.length} topics, each checked against hundreds of tests.`
                : "Loading the library…"}
            </p>
          </div>
          <Link to="/library" className={styles.secondary}>
            Search the whole library
          </Link>
        </div>
        {error && <p role="alert">{error}</p>}
        {!entries && !error && <p role="status">Loading…</p>}
        <TopicTiles topics={topics} />
      </section>
    </div>
  );
}
