import type { TreePanel } from "../api";
import type { Reserve } from "../player/reserve";
import { MarkLegend, markClasses, markOrder } from "./marks";
import styles from "./viz.module.css";

const COL = 46; // horizontal spacing: one column per node, in in-order
const ROW = 78; // vertical spacing per depth (room for pointer labels under a node)
const PAD = 26;
const R = 17;

export function TreeView({ panel, reserve }: { panel: TreePanel; reserve?: Reserve }) {
  const nodes = panel.nodes ?? [];
  // Sized for the widest and deepest the tree gets in this run, so it never changes height.
  const cols = Math.max(panel.width ?? 1, reserve?.treeWidth ?? 1, 1);
  const depth = Math.max(panel.height ?? 1, reserve?.treeHeight ?? 1, 1);
  const width = 2 * (PAD + R) + (cols - 1) * COL;
  const height = 2 * (PAD + R) + (depth - 1) * ROW + 20;
  const order = reserve?.marks.length ? reserve.marks : markOrder(nodes.map((n) => n.marks));
  if (!panel.defined || nodes.length === 0) {
    return <Empty panel={panel} width={width} height={height} text={panel.defined ? "Empty tree." : "Not defined yet."} />;
  }
  const pos = new Map(nodes.map((n) => [n.id, { x: PAD + R + n.x * COL, y: PAD + R + n.y * ROW }]));
  const pointersAt = (id: number) => (panel.pointers ?? []).filter((p) => p.node === id);
  const inOrder = [...nodes].sort((a, b) => a.x - b.x);
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <div className={styles.scroll}>
        <svg
          className={styles.svg}
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          style={{ maxWidth: "100%" }}
          role="img"
          aria-label={`${panel.label}: ${nodes.length} nodes`}
        >
          {(panel.edges ?? []).map((e) => {
            const a = pos.get(e.from)!;
            const b = pos.get(e.to)!;
            return <line key={`${e.from}-${e.to}`} className={styles.edge} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />;
          })}
          {nodes.map((n) => {
            const p = pos.get(n.id)!;
            return (
              <g key={n.id} className={`${styles.svgNode} ${markClasses(n.marks, order)}`}>
                <circle cx={p.x} cy={p.y} r={R} />
                <text x={p.x} y={p.y} className={styles.nodeText}>
                  {n.text}
                </text>
                {pointersAt(n.id).map((ptr, i) => (
                  <text key={ptr.label} x={p.x} y={p.y + R + 14 + i * 14} className={styles.svgPointer} data-pointer={ptr.label}>
                    ▲ {ptr.label}
                  </text>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
      <p className="sr-only">
        In order:{" "}
        {inOrder
          .map((n) => `${n.text}${n.marks.length ? ` (${n.marks.join(", ")})` : ""}${pointersAt(n.id).length ? ` [${pointersAt(n.id).map((p) => p.label).join(", ")}]` : ""}`)
          .join(", ")}
      </p>
      <MarkLegend items={inOrder.map((n) => ({ name: n.text, marks: n.marks }))} order={order} shape="node" />
    </section>
  );
}

function Empty({ panel, text, width, height }: { panel: { label: string }; text: string; width: number; height: number }) {
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <svg className={styles.svg} viewBox={`0 0 ${width} ${height}`} width={width} style={{ maxWidth: "100%" }} role="img" aria-label={`${panel.label}: ${text}`}>
        <text x={width / 2} y={height / 2} className={styles.nodeLabel}>
          {text}
        </text>
      </svg>
    </section>
  );
}
