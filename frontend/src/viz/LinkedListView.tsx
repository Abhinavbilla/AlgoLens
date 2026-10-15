import type { LinkedListPanel } from "../api";
import styles from "./viz.module.css";

export function LinkedListView({ panel }: { panel: LinkedListPanel }) {
  const nodes = panel.nodes ?? [];
  const pointers = panel.pointers ?? [];
  const at = (id: number | null) => pointers.filter((p) => p.node === id);
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      {!panel.defined ? (
        // Same wrapper as a real list, so the panel is the same height either way.
        <div className={styles.scroll}>
          <ol className={styles.linked}>
            <li className={styles.linkedItem}>
              <span className={`${styles.linkedNode} ${styles.nullNode}`}>not defined yet</span>
              <span className={styles.pointers} />
            </li>
          </ol>
        </div>
      ) : (
        <div className={styles.scroll}>
          <ol className={styles.linked}>
            {nodes.map((n, i) => (
              <li key={n.id} className={styles.linkedItem}>
                <span className={styles.linkedNode}>{n.text}</span>
                <span className={styles.linkedArrow} aria-hidden="true">
                  →
                </span>
                <span className={styles.pointers}>
                  {at(n.id).map((p) => (
                    <span key={p.label} className={styles.pointer} data-pointer={p.label}>
                      <span className={styles.arrow} aria-hidden="true">
                        ▲
                      </span>
                      <span className={styles.pointerLabel}>{p.label}</span>
                    </span>
                  ))}
                </span>
                <span className="sr-only">{i < nodes.length - 1 ? " then" : ""}</span>
              </li>
            ))}
            <li className={styles.linkedItem}>
              <span className={`${styles.linkedNode} ${styles.nullNode}`}>
                {panel.cycle_to != null ? `↺ back to ${nodes[panel.cycle_to]?.text}` : "null"}
              </span>
              <span className={styles.pointers}>
                {panel.cycle_to == null &&
                  at(null).map((p) => (
                    <span key={p.label} className={styles.pointer} data-pointer={p.label}>
                      <span className={styles.arrow} aria-hidden="true">
                        ▲
                      </span>
                      <span className={styles.pointerLabel}>{p.label}</span>
                    </span>
                  ))}
              </span>
            </li>
          </ol>
        </div>
      )}
    </section>
  );
}
