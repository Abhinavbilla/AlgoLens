import type { SequencePanel } from "../api";
import styles from "./viz.module.css";

// Stacks and queues are drawn as one horizontal row so their height never changes:
// a stack's top is its right end, a queue's front is its left end, both labelled in text.
export function SequenceView({ panel }: { panel: SequencePanel }) {
  const items = panel.items ?? [];
  const changed = new Set(panel.changed ?? []);
  const ends =
    panel.kind === "stack"
      ? { first: "bottom", last: "top" }
      : panel.kind === "queue"
        ? { first: "front", last: "back" }
        : null;
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      {!panel.defined || items.length === 0 ? (
        <div className={styles.scroll}>
          <ol className={styles.sequence}>
            <li className={`${styles.chip} ${styles.placeholderChip}`}>{panel.defined ? "Empty." : "Not defined yet."}</li>
          </ol>
        </div>
      ) : (
        <div className={styles.scroll}>
          <ol className={styles.sequence}>
            {items.map((text, i) => (
              <li key={i} className={`${styles.chip} ${changed.has(i) ? styles.changed : ""}`}>
                <span className={styles.chipText}>{text}</span>
                {changed.has(i) && (
                  <>
                    <span className={styles.changeMark} aria-hidden="true">
                      ✱
                    </span>
                    <span className="sr-only"> (changed)</span>
                  </>
                )}
                {ends && (i === 0 || i === items.length - 1) && (
                  <span className={styles.endLabel}>
                    {[i === 0 ? ends.first : "", i === items.length - 1 ? ends.last : ""].filter(Boolean).join(" · ")}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
