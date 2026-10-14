import type React from "react";
import { useRef } from "react";
import type { ArrayPanel } from "../api";
import { useKeepInView } from "./useKeepInView";
import styles from "./viz.module.css";

// Cells keep a fixed position: only their contents and markers change between steps.
// They shrink to fit narrow screens; only very long arrays scroll inside the panel.
// `pointerRows` reserves space for the most pointer labels that ever share one cell.
export function ArrayView({
  panel,
  pointerRows = 1,
  reserveRange = false,
}: {
  panel: ArrayPanel;
  pointerRows?: number;
  reserveRange?: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useKeepInView(scrollRef, JSON.stringify(panel.pointers ?? []));
  if (!panel.defined || !panel.items || panel.items.length === 0) {
    // Same rows as a populated array (index, cell, pointer labels), so the height never changes.
    return (
      <section className={styles.panel} aria-label={panel.label}>
        <h3 className={styles.title}>{panel.label}</h3>
        {reserveRange && <RangeLegend />}
        <div className={styles.scroll}>
          <ol className={styles.array} style={{ "--slots": 1, "--pointer-rows": pointerRows, minWidth: 0 } as React.CSSProperties}>
            <li className={styles.slot}>
              <span className={styles.index}>&nbsp;</span>
              <span className={`${styles.cell} ${styles.placeholderCell}`}>{panel.defined ? "empty" : "not defined yet"}</span>
              <span className={styles.pointers} />
            </li>
          </ol>
        </div>
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
      {range ? (
        <p className={styles.legend}>
          <span className={styles.rangeSwatch} aria-hidden="true" /> {range.label}:{" "}
          {range.from < range.to ? `positions ${range.from} to ${range.to - 1}` : "empty"}
        </p>
      ) : (
        reserveRange && <RangeLegend />
      )}
      <div className={styles.scroll} ref={scrollRef}>
        <ol
          className={styles.array}
          style={{ "--slots": slots, "--pointer-rows": pointerRows } as React.CSSProperties}
        >
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
              <li key={i} className={classes} data-keep-in-view={here.length ? "" : undefined}>
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
                    <span key={p.label} className={styles.pointer} data-pointer={p.label}>
                      <span className={styles.arrow} aria-hidden="true">
                        ▲
                      </span>
                      <span className={styles.pointerLabel}>{p.label}</span>
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

// Holds the range legend's line on steps without a range, so the cells don't move.
function RangeLegend() {
  return (
    <p className={styles.legend} aria-hidden="true">
      &nbsp;
    </p>
  );
}
