import type { MapPanel } from "../api";
import styles from "./viz.module.css";

export function MapView({ panel }: { panel: MapPanel }) {
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      {!panel.defined || !panel.entries ? (
        <p className={styles.muted}>Not defined yet.</p>
      ) : panel.entries.length === 0 ? (
        <p className={styles.muted}>Empty.</p>
      ) : (
        <table className={styles.map}>
          <thead>
            <tr>
              <th scope="col">Key</th>
              <th scope="col">Value</th>
            </tr>
          </thead>
          <tbody>
            {panel.entries.map((e) => (
              <tr key={e.key} className={e.changed ? styles.changed : ""}>
                <td>{e.key}</td>
                <td>
                  {e.value}
                  {e.changed && (
                    <>
                      <span className={styles.changeMark} aria-hidden="true">
                        ✱
                      </span>
                      <span className="sr-only"> (changed)</span>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
