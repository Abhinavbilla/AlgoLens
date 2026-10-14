import type { VarsPanel } from "../api";
import styles from "./viz.module.css";

export function VarsView({ panel }: { panel: VarsPanel }) {
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <dl className={styles.vars}>
        {panel.items.map((v) => (
          <div key={v.name} className={`${styles.var} ${v.changed ? styles.changed : ""}`}>
            <dt className={styles.varName}>{v.name}</dt>
            <dd className={styles.varValue}>
              {v.defined ? v.value : <span className={styles.muted}>not set</span>}
              {v.changed && (
                <>
                  <span className={styles.changeMark} aria-hidden="true">
                    ✱
                  </span>
                  <span className="sr-only"> (changed)</span>
                </>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
