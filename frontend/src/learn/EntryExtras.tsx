import { Link } from "react-router";
import { PATH } from "./path";
import { PRACTICE } from "./practice";
import styles from "./learn.module.css";
import { useProgress } from "./progress";

// Under an algorithm: mark it done, go to the next step on the path, and practise elsewhere.
export function EntryExtras({ slug }: { slug: string }) {
  const { done, toggle } = useProgress();
  const order = PATH.flatMap((s) => s.items);
  const at = order.indexOf(slug);
  const next = at >= 0 ? order.slice(at + 1).find(Boolean) : undefined;
  const nextHref = next?.startsWith("primer:") ? `/learn/${next.slice(7)}` : next ? `/library/${next}` : null;
  const practice = PRACTICE[slug] ?? [];
  const isDone = done.has(slug);

  return (
    <section className={styles.extras} aria-labelledby="practice-h">
      <div className={styles.primerFoot}>
        <button
          type="button"
          className={isDone ? styles.doneButtonOn : styles.doneButton}
          aria-pressed={isDone}
          onClick={() => toggle(slug)}
        >
          {isDone ? "✓ Marked as done" : "Mark as done"}
        </button>
        {nextHref && (
          <Link to={nextHref} className={styles.nextLink}>
            Next on the learning path →
          </Link>
        )}
      </div>
      {practice.length > 0 && (
        <>
          <h2 id="practice-h">Practice next</h2>
          <p className={styles.why}>
            Problems that use the same idea, easiest first. Try to solve them yourself before reading any
            solution.
          </p>
          <ul className={styles.practice}>
            {practice.map((p) => (
              <li key={p.url}>
                <a href={p.url} target="_blank" rel="noreferrer noopener">
                  {p.title}
                </a>
                <span className={styles[`level${p.level}`]}>{p.level}</span>
                <span className={styles.site}>{p.site}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
