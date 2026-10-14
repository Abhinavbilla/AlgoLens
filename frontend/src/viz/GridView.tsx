import { useRef } from "react";
import type { GridPanel } from "../api";
import type { Reserve } from "../player/reserve";
import { MarkLegend, markClasses, markOrder } from "./marks";
import { useKeepInView } from "./useKeepInView";
import styles from "./viz.module.css";

// Grids and 2D tables (e.g. dp). Cells keep their place; marks get a style per mark name
// plus a text legend, pointers are labelled tags inside their cell.
export function GridView({ panel, reserve }: { panel: GridPanel; reserve?: Reserve }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useKeepInView(scrollRef, JSON.stringify(panel.pointers ?? []));
  // Before the grid exists, draw blank cells at the largest size it reaches, so nothing moves.
  const blank = (n: number, m: number) =>
    Array.from({ length: n }, () => Array.from({ length: m }, () => ({ text: "", marks: [], changed: false })));
  const rows = panel.defined && panel.rows ? panel.rows : blank(reserve?.gridRows ?? 0, reserve?.gridCols ?? 0);
  const order = reserve?.marks.length ? reserve.marks : markOrder(rows.flat().map((c) => c.marks));
  const pointers = panel.pointers ?? [];
  // Header rows/columns exist whenever they exist at any step (blank until then).
  const NBSP = " "; // blank but with the same text metrics as a real label
  const colHeader = panel.col_header ?? (reserve?.gridColHeader ? rows[0]?.map(() => NBSP) ?? [] : null);
  const rowHeader = panel.row_header ?? (reserve?.gridRowHeader ? rows.map(() => NBSP) : null);
  const hasColHeader = !!colHeader;
  const hasRowHeader = !!rowHeader;
  const legendItems = rows.flatMap((row, r) => row.map((c, col) => ({ name: `(${r}, ${col})`, marks: c.marks })));
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <div className={styles.scroll} ref={scrollRef}>
        <div className={styles.overlayHost}>
        {/* An overlay on the table, not extra text in the layout, so the panel keeps its height. */}
        {!panel.defined && <span className={styles.overlayNote}>not defined yet</span>}
        <table className={styles.grid}>
          {hasColHeader && (
            <thead>
              <tr>
                {hasRowHeader && <th scope="col" />}
                {colHeader!.map((h, c) => (
                  <th key={c} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {rows.map((row, r) => (
              <tr key={r}>
                {hasRowHeader && <th scope="row">{rowHeader![r]}</th>}
                {row.map((cell, c) => {
                  const here = pointers.filter((p) => p.row === r && p.col === c);
                  return (
                    <td
                      key={c}
                      className={`${markClasses(cell.marks, order)} ${cell.changed ? styles.changedCell : ""}`}
                      data-keep-in-view={here.length ? "" : undefined}
                    >
                      <span className={styles.gridText}>{cell.text}</span>
                      {cell.changed && (
                        <>
                          <span className={styles.changeMark} aria-hidden="true">
                            ✱
                          </span>
                          <span className="sr-only"> (changed)</span>
                        </>
                      )}
                      {cell.marks.length > 0 && <span className="sr-only"> ({cell.marks.join(", ")})</span>}
                      {/* Always present (one line), so a pointer arriving never makes a row taller. */}
                      <span className={styles.cellPointers}>
                        {here.map((p) => (
                          <span key={p.label} className={styles.pointerLabel} data-pointer={p.label}>
                            {p.label}
                          </span>
                        ))}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
      <MarkLegend items={legendItems} order={order} />
    </section>
  );
}
