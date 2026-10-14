import { useState } from "react";
import { ApiError, api, type Comparison } from "../api";
import styles from "./solve.module.css";

// Distinct dash patterns as well as colours, so lines differ without colour.
const DASHES = ["", "6 4", "2 3", "10 3 2 3"];
const NUM = new Intl.NumberFormat("en-US");
const W = 640;
const H = 300;
const PAD = { left: 64, right: 16, top: 12, bottom: 44 };

export function Compare({ problemId }: { problemId: string }) {
  const [state, setState] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ok"; data: Comparison }
  >({ status: "idle" });

  async function load() {
    setState({ status: "loading" });
    try {
      setState({ status: "ok", data: await api.compare(problemId) });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof ApiError ? err.message : "Couldn't reach the server.",
      });
    }
  }

  return (
    <section className={styles.compare} aria-labelledby="compare-h">
      <h2 id="compare-h">How they scale</h2>
      <p className={styles.muted}>
        Each verified approach runs on the same inputs of growing size; the chart counts the lines of code it
        executes.
      </p>
      {state.status === "idle" && (
        <button type="button" onClick={load}>
          Run the comparison
        </button>
      )}
      {state.status === "loading" && <p role="status">Running each approach on bigger and bigger inputs…</p>}
      {state.status === "error" && <p role="alert">{state.message}</p>}
      {state.status === "ok" && <CompareChart data={state.data} />}
    </section>
  );
}

function ticks(lo: number, hi: number) {
  const out: number[] = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) out.push(10 ** e);
  return out;
}

const fmt = (v: number) =>
  v >= 1e6 ? `${+(v / 1e6).toPrecision(3)}M` : v >= 1e3 ? `${+(v / 1e3).toPrecision(3)}k` : `${v}`;

export function CompareChart({ data }: { data: Comparison }) {
  const sizes = data.sizes.filter((n) => n > 0);
  const all = data.series.flatMap((s) =>
    s.points.filter((p) => p.ops !== null && p.n > 0).map((p) => p.ops as number),
  );
  if (sizes.length < 2 || all.length === 0)
    return <p>Not enough sizes could be generated to draw a chart.</p>;
  const xs = ticks(Math.min(...sizes), Math.max(...sizes));
  const ys = ticks(Math.max(1, Math.min(...all)), Math.max(...all));
  const lx = (n: number) =>
    PAD.left +
    ((Math.log10(n) - Math.log10(xs[0])) / (Math.log10(xs[xs.length - 1]) - Math.log10(xs[0]) || 1)) *
      (W - PAD.left - PAD.right);
  const ly = (v: number) =>
    H -
    PAD.bottom -
    ((Math.log10(v) - Math.log10(ys[0])) / (Math.log10(ys[ys.length - 1]) - Math.log10(ys[0]) || 1)) *
      (H - PAD.top - PAD.bottom);

  return (
    <figure className={styles.figure}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Lines executed against input size, both on log scales"
        className={styles.chart}
      >
        {xs.map((t) => (
          <g key={`x${t}`}>
            <line x1={lx(t)} x2={lx(t)} y1={PAD.top} y2={H - PAD.bottom} className={styles.grid} />
            <text x={lx(t)} y={H - PAD.bottom + 16} textAnchor="middle" className={styles.tick}>
              {fmt(t)}
            </text>
          </g>
        ))}
        {ys.map((t) => (
          <g key={`y${t}`}>
            <line x1={PAD.left} x2={W - PAD.right} y1={ly(t)} y2={ly(t)} className={styles.grid} />
            <text x={PAD.left - 6} y={ly(t) + 4} textAnchor="end" className={styles.tick}>
              {fmt(t)}
            </text>
          </g>
        ))}
        <text x={(PAD.left + W - PAD.right) / 2} y={H - 6} textAnchor="middle" className={styles.axis}>
          input size n
        </text>
        <text
          x={14}
          y={(PAD.top + H - PAD.bottom) / 2}
          textAnchor="middle"
          className={styles.axis}
          transform={`rotate(-90 14 ${(PAD.top + H - PAD.bottom) / 2})`}
        >
          lines executed
        </text>
        {data.series.map((s, i) => {
          const pts = s.points.filter((p) => p.ops !== null && p.n > 0);
          return (
            <g key={s.id} className={styles[`series${i % 4}`]}>
              <polyline
                points={pts.map((p) => `${lx(p.n)},${ly(p.ops as number)}`).join(" ")}
                fill="none"
                strokeWidth={2.5}
                strokeDasharray={DASHES[i % DASHES.length]}
              />
              {pts.map((p) => (
                <circle key={p.n} cx={lx(p.n)} cy={ly(p.ops as number)} r={3.5} />
              ))}
            </g>
          );
        })}
      </svg>
      <figcaption>
        <ul className={styles.legend}>
          {data.series.map((s, i) => (
            <li key={s.id} className={styles[`series${i % 4}`]}>
              <svg width="36" height="10" aria-hidden="true">
                <line
                  x1="0"
                  x2="36"
                  y1="5"
                  y2="5"
                  strokeWidth={2.5}
                  strokeDasharray={DASHES[i % DASHES.length]}
                />
              </svg>{" "}
              {s.name}
              {s.points.some((p) => p.ops === null) && (
                <span className={styles.muted}>
                  {" "}
                  (stopped: too slow from n = {s.points.find((p) => p.ops === null)?.n} with a{" "}
                  {data.limits.cpu_ms / 1000} s limit)
                </span>
              )}
            </li>
          ))}
        </ul>
      </figcaption>
      <table className={styles.table}>
        <caption>Lines executed at each size</caption>
        <thead>
          <tr>
            <th scope="col">n</th>
            {data.series.map((s) => (
              <th scope="col" key={s.id}>
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.sizes.map((n) => (
            <tr key={n}>
              <th scope="row">{NUM.format(n)}</th>
              {data.series.map((s) => {
                const p = s.points.find((q) => q.n === n);
                return <td key={s.id}>{p?.ops != null ? NUM.format(p.ops) : (p?.status ?? "")}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
