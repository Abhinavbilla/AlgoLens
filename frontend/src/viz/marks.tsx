import styles from "./viz.module.css";

// Marks ("visited", "in heap", "wall", ...) are drawn with a distinct style per mark name,
// in the order they first appear in the animation, and always named in a text legend:
// never colour alone. The legend lists every mark the animation uses, one line each, so its
// height never changes between steps.
const STYLES = [styles.mark0, styles.mark1, styles.mark2, styles.mark3];

export function markOrder(lists: string[][]): string[] {
  const seen: string[] = [];
  for (const marks of lists) for (const m of marks) if (!seen.includes(m)) seen.push(m);
  return seen;
}

export function markClasses(marks: string[], order: string[]): string {
  return marks.map((m) => STYLES[order.indexOf(m) % STYLES.length]).join(" ");
}

/** "in heap: 1, 3", one line per mark. `items` pairs a display name with its marks.
 *  `shape` makes each swatch look exactly like the marked thing: a cell or a node. */
export function MarkLegend({
  items,
  order,
  shape = "cell",
}: {
  items: { name: string; marks: string[] }[];
  order: string[];
  shape?: "cell" | "node";
}) {
  if (!order.length) return null;
  return (
    <ul className={styles.legendList}>
      {order.map((m, i) => {
        const names = items.filter((it) => it.marks.includes(m)).map((it) => it.name);
        const text = names.length ? names.join(", ") : "none";
        return (
          <li key={m} title={`${m}: ${text}`}>
            {shape === "node" ? (
              <svg className={styles.nodeSwatch} viewBox="0 0 20 20" aria-hidden="true">
                <g className={`${styles.svgNode} ${STYLES[i % STYLES.length]}`}>
                  <circle cx="10" cy="10" r="7" />
                </g>
              </svg>
            ) : (
              <span className={`${styles.swatch} ${STYLES[i % STYLES.length]}`} aria-hidden="true" />
            )}
            <strong>{m}:</strong> {text}
          </li>
        );
      })}
    </ul>
  );
}
