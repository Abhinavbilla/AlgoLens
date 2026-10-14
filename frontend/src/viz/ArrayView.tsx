import type { ArrayPanel } from "../api";
import styles from "./viz.module.css";

// Cells keep a fixed position: only their contents and markers change between steps.
export function ArrayView({ panel }: { panel: ArrayPanel }) {
  if (!panel.defined || !panel.items) {
    return (
      <section className={styles.panel} aria-label={panel.label}>
        <h3 className={styles.title}>{panel.label}</h3>
        <p className={styles.muted}>Not defined yet.</p>
      </section>
    );
  }
  const items = panel.items;
  const changed = new Set(panel.changed ?? []);
  const pointers = panel.pointers ?? [];
  const range = panel.range;
  // One extra slot when a pointer sits one past the end (e.g. hi = len(nums)).
  const slots = pointers.some((p) => p.index === items.length) ? items.length + 1 : items.length;
  const inRange = (i: number) => !!range && i >= range.from && i < range.to;

  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      {range && (
        <p className={styles.legend}>
          <span className={styles.rangeSwatch} aria-hidden="true" /> {range.label}:{" "}
          {range.from < range.to ? `positions ${range.from} to ${range.to - 1}` : "empty"}
        </p>
      )}
      <div className={styles.scroll}>
        <ol className={styles.array} style={{ gridTemplateColumns: `repeat(${slots}, var(--cell))` }}>
          {Array.from({ length: slots }, (_, i) => {
            const here = pointers.filter((p) => p.index === i);
            const isPhantom = i >= items.length;
            const classes = [
              styles.slot,
              changed.has(i) ? styles.changed : "",
              inRange(i) ? styles.inRange : range ? styles.outOfRange : "",
              isPhantom ? styles.phantom : "",
            ].join(" ");
            return (
              <li key={i} className={classes}>
                <span className={styles.index}>{isPhantom ? "end" : i}</span>
                <span className={styles.cell}>
                  {isPhantom ? "" : items[i]}
                  {changed.has(i) && (
                    <>
                      <span className={styles.changeMark} aria-hidden="true">
                        ✱
                      </span>
                      <span className="sr-only"> (changed)</span>
                    </>
                  )}
                </span>
                <span className={styles.pointers}>
                  {here.map((p) => (
                    <span key={p.label} className={styles.pointer}>
                      <span aria-hidden="true">▲</span> {p.label}
                    </span>
                  ))}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
