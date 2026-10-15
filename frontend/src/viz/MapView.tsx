import type { MapPanel } from "../api";
import styles from "./viz.module.css";

// The table always has as many rows as the map ever holds in this run (`minRows`); the rows
// not in use yet are invisible placeholders, so the panel is the same height at every step.
export function MapView({ panel, minRows = 0 }: { panel: MapPanel; minRows?: number }) {
  const entries = panel.defined ? (panel.entries ?? []) : [];
  const note = !panel.defined || !panel.entries ? "Not defined yet." : entries.length === 0 ? "Empty." : null;
  const used = entries.length + (note ? 1 : 0);
  const filler = Math.max(0, Math.max(minRows, 1) - used);
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <table className={styles.map}>
        <thead>
          <tr>
            <th scope="col">Key</th>
            <th scope="col">Value</th>
          </tr>
        </thead>
        <tbody>
          {note && (
            <tr>
              <td colSpan={2} className={styles.muted}>
                {note}
              </td>
            </tr>
          )}
          {entries.map((e) => (
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
          {Array.from({ length: filler }, (_, i) => (
            <tr key={`filler-${i}`} className={styles.placeholderRow} aria-hidden="true">
              <td>&nbsp;</td>
              <td>&nbsp;</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
