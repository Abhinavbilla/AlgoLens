import { useId } from "react";
import type { GraphPanel } from "../api";
import { MarkLegend, markClasses, markOrder } from "./marks";
import styles from "./viz.module.css";

const SIZE = 320; // the backend's layout is in [0, 1]; nodes never move between steps
const R = 16;

export function GraphView({ panel, markNames }: { panel: GraphPanel; markNames?: string[] }) {
  const arrowId = useId();
  const nodes = panel.nodes ?? [];
  if (!panel.defined) {
    return (
      <section className={styles.panel} aria-label={panel.label}>
        <h3 className={styles.title}>{panel.label}</h3>
        <svg
          className={styles.svg}
          viewBox={`-30 -30 ${SIZE + 60} ${SIZE + 60}`}
          role="img"
          aria-label={`${panel.label}: not defined yet`}
        >
          <text x={SIZE / 2} y={SIZE / 2} className={styles.nodeLabel}>
            Not defined yet.
          </text>
        </svg>
      </section>
    );
  }
  const order = markNames?.length ? markNames : markOrder(nodes.map((n) => n.marks));
  const at = (id: number) => {
    const n = nodes[id];
    return { x: n.x * SIZE, y: n.y * SIZE };
  };
  const pointersAt = (id: number) => (panel.pointers ?? []).filter((p) => p.node === id);
  return (
    <section className={styles.panel} aria-label={panel.label}>
      <h3 className={styles.title}>{panel.label}</h3>
      <svg
        className={styles.svg}
        viewBox={`-30 -30 ${SIZE + 60} ${SIZE + 60}`}
        role="img"
        aria-label={`${panel.label}: ${nodes.length} nodes, ${(panel.edges ?? []).length} edges`}
      >
        {panel.directed && (
          <defs>
            <marker
              id={arrowId}
              viewBox="0 0 10 10"
              refX="10"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto"
            >
              <path d="M0,0 L10,5 L0,10 z" className={styles.arrowHead} />
            </marker>
          </defs>
        )}
        {(panel.edges ?? []).map((e, i) => {
          const a = at(e.u);
          const b = at(e.v);
          const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
          const [dx, dy] = [((b.x - a.x) / len) * R, ((b.y - a.y) / len) * R];
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          return (
            <g key={i}>
              <line
                className={styles.edge}
                x1={a.x + dx}
                y1={a.y + dy}
                x2={b.x - dx}
                y2={b.y - dy}
                markerEnd={panel.directed ? `url(#${arrowId})` : undefined}
              />
              {e.w !== null && (
                <>
                  <rect x={mx - 11} y={my - 9} width={22} height={18} rx={4} className={styles.weightBox} />
                  <text x={mx} y={my} className={styles.weightText}>
                    {e.w}
                  </text>
                </>
              )}
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = at(n.id);
          return (
            <g key={n.id} className={`${styles.svgNode} ${markClasses(n.marks, order)}`}>
              <circle cx={p.x} cy={p.y} r={R} />
              <text x={p.x} y={p.y} className={styles.nodeText}>
                {n.id}
              </text>
              {n.label !== null && (
                <text x={p.x} y={p.y + R + 13} className={styles.nodeLabel}>
                  {n.label}
                </text>
              )}
              {pointersAt(n.id).map((ptr, i) => (
                <text
                  key={ptr.label}
                  x={p.x}
                  y={p.y - R - 6 - i * 13}
                  className={styles.svgPointer}
                  data-pointer={ptr.label}
                >
                  {ptr.label} ▼
                </text>
              ))}
            </g>
          );
        })}
      </svg>
      <p className="sr-only">
        {nodes
          .map(
            (n) =>
              `node ${n.id}${n.label !== null ? ` label ${n.label}` : ""}${n.marks.length ? ` (${n.marks.join(", ")})` : ""}${
                pointersAt(n.id).length
                  ? ` [${pointersAt(n.id)
                      .map((p) => p.label)
                      .join(", ")}]`
                  : ""
              }`,
          )
          .join("; ")}
      </p>
      <MarkLegend
        items={nodes.map((n) => ({ name: String(n.id), marks: n.marks }))}
        order={order}
        shape="node"
      />
    </section>
  );
}
