import type { StackEntry } from "../api";
import styles from "./viz.module.css";

// Innermost call on top. A call that started at this step is marked "new" in text.
export function CallStack({ stack }: { stack: StackEntry[] }) {
  const innermostFirst = [...stack].reverse();
  return (
    <section className={styles.panel} aria-label="Call stack">
      <h3 className={styles.title}>Call stack</h3>
      <ol className={styles.stack}>
        {innermostFirst.map((s, i) => (
          <li key={s.aid} className={i === 0 ? styles.current : ""}>
            <code>{s.call}</code>
            <span className={styles.stackLine}>line {s.line}</span>
            {s.new && <span className={styles.badge}>new</span>}
            {i === 0 && <span className="sr-only"> (running)</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
