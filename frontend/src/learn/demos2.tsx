import { useState } from "react";
import styles from "./demos.module.css";

// Widgets for strings, sets, bits, number basics and sorting stability. Same rules as
// demos.tsx: driven by buttons and inputs, and every change is said in words.

function Said({ text }: { text: string }) {
  return (
    <p className={styles.said} role="status">
      {text}
    </p>
  );
}

/* --- strings ----------------------------------------------------------------------------- */

const WORD = "algorithm";

export function SubstringDemo() {
  const [start, setStart] = useState(2);
  const [end, setEnd] = useState(6);
  const s = Math.min(start, end);
  const e = Math.max(start, end);
  return (
    <div className={styles.demo}>
      <ol className={styles.chars} aria-label={`The string "${WORD}", one character per box`}>
        {[...WORD].map((c, i) => (
          <li key={i} className={i >= s && i < e ? styles.inSlice : undefined}>
            <span className={styles.charIndex}>{i}</span>
            <span className={styles.charBox}>{c}</span>
          </li>
        ))}
      </ol>
      <div className={styles.sliders}>
        <label>
          start <output>{start}</output>
          <input
            type="range"
            min={0}
            max={WORD.length}
            value={start}
            onChange={(ev) => setStart(+ev.target.value)}
          />
        </label>
        <label>
          end <output>{end}</output>
          <input
            type="range"
            min={0}
            max={WORD.length}
            value={end}
            onChange={(ev) => setEnd(+ev.target.value)}
          />
        </label>
      </div>
      <Said
        text={`s[${s}:${e}] is "${WORD.slice(s, e)}": positions ${s} up to, but not including, ${e}. That's ${e - s} character${e - s === 1 ? "" : "s"}.`}
      />
    </div>
  );
}

export function BuildStringDemo() {
  const [n, setN] = useState(10);
  const copying = (n * (n + 1)) / 2;
  const max = 50 * 51;
  return (
    <div className={styles.demo}>
      <label className={styles.inline}>
        Build a string of <output>{n}</output> characters
        <input type="range" min={1} max={50} value={n} onChange={(e) => setN(+e.target.value)} />
      </label>
      <div className={styles.costBars}>
        <div>
          <span>
            <code>s += c</code> in a loop
          </span>
          <span className={styles.costBar} style={{ width: `${(100 * copying) / max}%` }} />
          <strong>{copying.toLocaleString("en-US")} characters copied</strong>
        </div>
        <div>
          <span>
            <code>"".join(parts)</code>
          </span>
          <span className={styles.costBarGood} style={{ width: `${Math.max(1, (100 * n) / max)}%` }} />
          <strong>{n} characters copied</strong>
        </div>
      </div>
      <Said
        text={`Strings can't be changed in place, so each += makes a whole new copy: 1 + 2 + … + ${n} = ${copying.toLocaleString("en-US")} characters. Collecting the pieces and joining once copies each character a single time.`}
      />
    </div>
  );
}

/* --- sets -------------------------------------------------------------------------------- */

const A = [1, 2, 3, 4, 5];
const B = [4, 5, 6, 7];
type SetOp = "union" | "intersection" | "difference";
const OPS: Record<SetOp, { label: string; code: string; pick: (x: number) => boolean; say: string }> = {
  union: {
    label: "A | B",
    code: "A | B",
    pick: (x) => A.includes(x) || B.includes(x),
    say: "everything in either set",
  },
  intersection: {
    label: "A & B",
    code: "A & B",
    pick: (x) => A.includes(x) && B.includes(x),
    say: "only what's in both",
  },
  difference: {
    label: "A - B",
    code: "A - B",
    pick: (x) => A.includes(x) && !B.includes(x),
    say: "what's in A but not in B",
  },
};

export function SetDemo() {
  const [op, setOp] = useState<SetOp>("intersection");
  const [probe, setProbe] = useState("6");
  const all = [...new Set([...A, ...B])].sort((a, b) => a - b);
  const result = all.filter(OPS[op].pick);
  const v = Number(probe);
  return (
    <div className={styles.demo}>
      <div className={styles.setRows}>
        <p>
          <strong>A</strong>{" "}
          {A.map((x) => (
            <span key={x} className={result.includes(x) ? styles.chipOn : styles.chip}>
              {x}
            </span>
          ))}
        </p>
        <p>
          <strong>B</strong>{" "}
          {B.map((x) => (
            <span key={x} className={result.includes(x) ? styles.chipOn : styles.chip}>
              {x}
            </span>
          ))}
        </p>
      </div>
      <div className={styles.buttons}>
        {(Object.keys(OPS) as SetOp[]).map((k) => (
          <button key={k} type="button" aria-pressed={op === k} onClick={() => setOp(k)}>
            {OPS[k].label}
          </button>
        ))}
      </div>
      <Said text={`${OPS[op].code} is {${result.join(", ")}}: ${OPS[op].say}.`} />
      <div className={styles.hashInput}>
        <label>
          Is it in A? <input value={probe} onChange={(e) => setProbe(e.target.value)} inputMode="numeric" />
        </label>
        <span role="status">
          {probe.trim() === "" || Number.isNaN(v)
            ? "Type a number."
            : A.includes(v)
              ? `Yes: ${v} in A is True, found in one hash lookup.`
              : `No: ${v} in A is False, also one lookup. No scanning.`}
        </span>
      </div>
    </div>
  );
}

/* --- bits -------------------------------------------------------------------------------- */

const bitsOf = (n: number) => Array.from({ length: 8 }, (_, i) => (n >> (7 - i)) & 1);

export function BitsDemo() {
  const [n, setN] = useState(44);
  const [said, setSaid] = useState("Each box is a bit. Tap one to flip it, or try an operation.");
  const set = (v: number, why: string) => {
    setN(v & 255);
    setSaid(why);
  };
  const ones = bitsOf(n).filter(Boolean).length;
  return (
    <div className={styles.demo}>
      <ol className={styles.bits} aria-label={`${n} in binary: ${bitsOf(n).join("")}`}>
        {bitsOf(n).map((b, i) => {
          const place = 1 << (7 - i);
          return (
            <li key={i}>
              <span className={styles.charIndex}>{place}</span>
              <button
                type="button"
                className={b ? styles.bitOn : styles.bitOff}
                aria-label={`bit worth ${place}: ${b}`}
                onClick={() =>
                  set(
                    n ^ place,
                    `Flipped the bit worth ${place}: ${b ? "subtract" : "add"} ${place}, giving ${n ^ place}.`,
                  )
                }
              >
                {b}
              </button>
            </li>
          );
        })}
      </ol>
      <p className={styles.formula}>
        ={" "}
        {bitsOf(n)
          .map((b, i) => (b ? 1 << (7 - i) : 0))
          .filter(Boolean)
          .join(" + ") || "0"}{" "}
        = <strong>{n}</strong> · {ones} one-bit{ones === 1 ? "" : "s"}
      </p>
      <div className={styles.buttons}>
        <button
          type="button"
          onClick={() =>
            set(n << 1, `n << 1 shifts every bit left: ${n} × 2 = ${(n << 1) & 255} (bits past 8 fall off).`)
          }
        >
          n &lt;&lt; 1
        </button>
        <button
          type="button"
          onClick={() => set(n >> 1, `n >> 1 shifts every bit right: ${n} // 2 = ${n >> 1}.`)}
        >
          n &gt;&gt; 1
        </button>
        <button
          type="button"
          disabled={n === 0}
          onClick={() =>
            set(
              n & (n - 1),
              `n & (n - 1) clears the lowest 1-bit: ${n} becomes ${n & (n - 1)}. Repeat until 0 to count the 1-bits.`,
            )
          }
        >
          n &amp; (n - 1)
        </button>
        <button
          type="button"
          onClick={() => set(n ^ 255, `n ^ 255 flips all 8 bits: ${n} becomes ${n ^ 255}.`)}
        >
          n ^ 255
        </button>
      </div>
      <Said
        text={`${said} ${n & 1 ? `${n} is odd: its last bit is 1.` : `${n} is even: its last bit is 0.`}`}
      />
    </div>
  );
}

/* --- number basics ----------------------------------------------------------------------- */

export function ModuloDemo() {
  const [k, setK] = useState(7);
  const [n, setN] = useState(23);
  const r = ((n % k) + k) % k;
  const R = 70;
  return (
    <div className={styles.demo}>
      <div className={styles.twoUp}>
        <svg
          viewBox="-100 -100 200 200"
          className={styles.clock}
          role="img"
          aria-label={`${n} mod ${k} is ${r}`}
        >
          <circle r={R} className={styles.clockFace} />
          {Array.from({ length: k }, (_, i) => {
            const a = (2 * Math.PI * i) / k - Math.PI / 2;
            return (
              <g key={i} className={i === r ? styles.svgHot : undefined}>
                <circle cx={R * Math.cos(a)} cy={R * Math.sin(a)} r={14} />
                <text x={R * Math.cos(a)} y={R * Math.sin(a)}>
                  {i}
                </text>
              </g>
            );
          })}
        </svg>
        <div className={styles.sliders}>
          <label>
            n <output>{n}</output>
            <input type="range" min={0} max={60} value={n} onChange={(e) => setN(+e.target.value)} />
          </label>
          <label>
            k <output>{k}</output>
            <input type="range" min={2} max={12} value={k} onChange={(e) => setK(+e.target.value)} />
          </label>
        </div>
      </div>
      <Said
        text={`${n} mod ${k} = ${r}: walk ${n} steps around a clock with ${k} positions and you stop at ${r}. That's also the remainder of ${n} ÷ ${k} (${Math.floor(n / k)} × ${k} + ${r}).`}
      />
    </div>
  );
}

export function DigitsDemo() {
  const [n, setN] = useState(4096);
  const [left, setLeft] = useState(4096);
  const [digits, setDigits] = useState<number[]>([]);
  const reset = (v: number) => {
    setN(v);
    setLeft(v);
    setDigits([]);
  };
  return (
    <div className={styles.demo}>
      <div className={styles.hashInput}>
        <label>
          Number{" "}
          <input
            value={n}
            inputMode="numeric"
            onChange={(e) =>
              reset(Math.max(0, Math.min(999999, Number(e.target.value.replace(/\D/g, "")) || 0)))
            }
          />
        </label>
        <button
          type="button"
          disabled={left === 0}
          onClick={() => {
            setDigits([left % 10, ...digits]);
            setLeft(Math.floor(left / 10));
          }}
        >
          Take the last digit
        </button>
        <button type="button" onClick={() => reset(n)}>
          Start over
        </button>
      </div>
      <p className={styles.formula}>
        left: <strong>{left}</strong> · digits found: <strong>{digits.join(" ") || "none yet"}</strong>
      </p>
      <Said
        text={
          left === 0
            ? `Done: ${n} has ${digits.length || 1} digit${digits.length === 1 ? "" : "s"}. The number of steps grows like log₁₀ n, not like n.`
            : `n % 10 is the last digit (${left % 10}); n // 10 drops it (${Math.floor(left / 10)}). Repeat until nothing is left.`
        }
      />
    </div>
  );
}

/* --- sorting stability ------------------------------------------------------------------- */

const STUDENTS = [
  { name: "Asha", grade: "B" },
  { name: "Ben", grade: "A" },
  { name: "Chen", grade: "B" },
  { name: "Dev", grade: "A" },
  { name: "Ema", grade: "B" },
];

export function StabilityDemo() {
  const [mode, setMode] = useState<"original" | "stable" | "unstable">("original");
  const stable = [...STUDENTS].sort((a, b) => a.grade.localeCompare(b.grade));
  // An unstable result a real unstable sort can produce: same grades, ties in another order.
  const unstable = [STUDENTS[3], STUDENTS[1], STUDENTS[4], STUDENTS[0], STUDENTS[2]];
  const rows = mode === "original" ? STUDENTS : mode === "stable" ? stable : unstable;
  return (
    <div className={styles.demo}>
      <div className={styles.buttons}>
        <button type="button" aria-pressed={mode === "original"} onClick={() => setMode("original")}>
          In name order
        </button>
        <button type="button" aria-pressed={mode === "stable"} onClick={() => setMode("stable")}>
          Sort by grade, stable
        </button>
        <button type="button" aria-pressed={mode === "unstable"} onClick={() => setMode("unstable")}>
          Sort by grade, unstable
        </button>
      </div>
      <ol className={styles.cardsRow} aria-label="Students in the current order">
        {rows.map((s) => (
          <li key={s.name} className={s.grade === "B" ? styles.cardB : styles.cardA}>
            <strong>{s.name}</strong> <span>grade {s.grade}</span>
          </li>
        ))}
      </ol>
      <Said
        text={
          mode === "original"
            ? "The students start in name order. Now sort them by grade."
            : mode === "stable"
              ? "Stable: within each grade, the names are still in their original order (Ben before Dev; Asha, Chen, Ema)."
              : "Unstable: the grades are sorted, but students with the same grade got shuffled (Dev before Ben). Nothing is wrong with the grades, but the earlier order is lost."
        }
      />
    </div>
  );
}
