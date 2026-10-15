import { useEffect, useMemo, useState } from "react";
import styles from "./home.module.css";

// The hero's moving picture: an actual bubble sort, step by step, with the same kind of
// one-line narration the player shows. Every frame below is computed by running the
// algorithm, so even the decoration is honest.

type Step = {
  values: number[];
  compare: [number, number] | null;
  swapped: boolean;
  sorted: number;
  text: string;
};

function bubbleSortSteps(input: number[]): Step[] {
  const a = [...input];
  const steps: Step[] = [
    { values: [...a], compare: null, swapped: false, sorted: 0, text: "Unsorted. Let's bubble." },
  ];
  for (let i = 0; i < a.length - 1; i++) {
    for (let j = 0; j < a.length - 1 - i; j++) {
      const out = a[j] > a[j + 1];
      steps.push({
        values: [...a],
        compare: [j, j + 1],
        swapped: false,
        sorted: i,
        text: out ? `${a[j]} > ${a[j + 1]}: out of order` : `${a[j]} ≤ ${a[j + 1]}: fine`,
      });
      if (out) {
        [a[j], a[j + 1]] = [a[j + 1], a[j]];
        steps.push({ values: [...a], compare: [j, j + 1], swapped: true, sorted: i, text: `Swap them` });
      }
    }
  }
  steps.push({ values: [...a], compare: null, swapped: false, sorted: a.length, text: "Sorted." });
  return steps;
}

const INPUT = [5, 2, 8, 3, 9, 1, 6, 4];
const MAX = Math.max(...INPUT);

export function SortingPreview() {
  const steps = useMemo(() => bubbleSortSteps(INPUT), []);
  const [i, setI] = useState(0);
  const reduced =
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (reduced) return;
    const last = i === steps.length - 1;
    const t = window.setTimeout(() => setI(last ? 0 : i + 1), last ? 2200 : i === 0 ? 1400 : 650);
    return () => window.clearTimeout(t);
  }, [i, steps.length, reduced]);

  const s = steps[i];
  const n = s.values.length;
  return (
    <figure className={styles.preview} aria-label="A bubble sort running, step by step">
      <div className={styles.previewTop} aria-hidden="true">
        <span className={styles.previewDots}>
          <span />
          <span />
          <span />
        </span>
        <span className={styles.previewFile}>bubble_sort.py</span>
        <span className={styles.previewStep}>
          step {i + 1} / {steps.length}
        </span>
      </div>
      <div className={styles.bars} aria-hidden="true">
        {s.values.map((v, k) => {
          const active = s.compare?.includes(k);
          const done = k >= n - s.sorted;
          return (
            <div
              key={k}
              className={[
                styles.bar,
                active ? (s.swapped ? styles.barSwap : styles.barCompare) : "",
                done ? styles.barDone : "",
              ].join(" ")}
              style={{ height: `${18 + (v / MAX) * 82}%` }}
            >
              <span>{v}</span>
            </div>
          );
        })}
      </div>
      <figcaption className={styles.previewCaption}>
        <span className={styles.previewArrow} aria-hidden="true">
          ▸
        </span>{" "}
        {s.text}
      </figcaption>
      {reduced && (
        <div className={styles.previewControls}>
          <button type="button" onClick={() => setI((i + 1) % steps.length)}>
            Next step
          </button>
        </div>
      )}
    </figure>
  );
}
