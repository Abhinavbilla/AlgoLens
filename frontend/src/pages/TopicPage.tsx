import { Link, useParams } from "react-router";
import { TopicIcon } from "../TopicIcon";
import styles from "./home.module.css";
import { EntryCards, useLibrary, useTopics } from "./libraryData";

// One topic per page: short to scroll on a phone, with the neighbouring topics a tap away.
export function TopicPage() {
  const { id = "" } = useParams();
  const { entries, error } = useLibrary();
  const topics = useTopics(entries);
  const at = topics.findIndex((t) => t.section.id === id);
  const topic = topics[at];

  if (error) return <p role="alert">{error}</p>;
  if (!entries) return <p role="status">Loading…</p>;
  if (!topic) {
    return (
      <section className={styles.page}>
        <h1 className={styles.pageTitle}>No such topic</h1>
        <p>
          <Link to="/library">See every topic in the library</Link>
        </p>
      </section>
    );
  }
  const prev = topics[at - 1];
  const next = topics[at + 1];

  return (
    <article className={styles.page}>
      <p className={styles.crumbs}>
        <Link to="/library">Library</Link> / {topic.section.title}
      </p>
      <header className={styles.topicHead}>
        <span className={styles.topicIcon}>
          <TopicIcon topic={topic.section.id} size={52} />
        </span>
        <div>
          <h1 className={styles.pageTitle}>{topic.section.title}</h1>
          <p className={styles.topicIntro}>{topic.section.intro}</p>
          <p className={styles.libraryMeta}>
            {topic.items.length} algorithm{topic.items.length === 1 ? "" : "s"}, each ready to watch step by step.
          </p>
        </div>
      </header>
      <EntryCards items={topic.items} />
      <nav className={styles.pager} aria-label="Other topics">
        {prev ? (
          <Link to={`/topics/${prev.section.id}`} className={styles.pagerLink}>
            <span>← Previous topic</span>
            <strong>{prev.section.title}</strong>
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link to={`/topics/${next.section.id}`} className={`${styles.pagerLink} ${styles.pagerNext}`}>
            <span>Next topic →</span>
            <strong>{next.section.title}</strong>
          </Link>
        ) : (
          <Link to="/library" className={`${styles.pagerLink} ${styles.pagerNext}`}>
            <span>That's every topic</span>
            <strong>Back to the library</strong>
          </Link>
        )}
      </nav>
    </article>
  );
}
