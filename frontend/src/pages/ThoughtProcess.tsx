import { Link } from "react-router";
import type { Explanation } from "../api";
import styles from "./thinking.module.css";

// The interview-style walk from brute force to optimal. The prose is AI-written about code that
// was run and verified; the page says so, and links each data structure to its hands-on primer.

const PRIMER_FOR: [RegExp, string, string][] = [
  [/hash|dict|map/i, "/learn/hashing", "a hash map"],
  [/\bset\b/i, "/learn/sets", "a set"],
  [/stack|queue|deque/i, "/learn/stacks-queues", "a stack or queue"],
  [/heap|priority/i, "/library/heap-operations", "a heap"],
  [/linked/i, "/learn/linked-lists", "a linked list"],
  [/tree|bst/i, "/learn/trees", "a tree"],
  [/graph|adjacen/i, "/learn/graphs", "a graph"],
  [/string|char/i, "/learn/strings", "a string"],
  [/bit/i, "/learn/bits", "bit manipulation"],
  [/array|list|prefix|window|pointer/i, "/learn/arrays", "an array"],
];

export function primerFor(name: string): { href: string; what: string } | null {
  const hit = PRIMER_FOR.find(([re]) => re.test(name));
  return hit ? { href: hit[1], what: hit[2] } : null;
}

export function stageLabel(i: number, count: number, isBrute: boolean): string {
  if (isBrute || i === 0) return "Brute force";
  if (i === count - 1) return "Optimal";
  return "Better";
}

export function ThoughtProcess({ explanation: e }: { explanation: Explanation }) {
  const n = e.approaches.length;
  return (
    <section className={styles.thinking} aria-labelledby="thinking-h">
      <header className={styles.head}>
        <p className={styles.eyebrow}>The thought process</p>
        <h2 id="thinking-h">How to think about it</h2>
        <p className={styles.note}>
          This walkthrough is written by AI, based on code that's been run and checked. If anything here ever
          disagrees with the code or the animation, trust those.
        </p>
      </header>

      <div className={styles.understand}>
        <h3>1 · Understand the problem</h3>
        <p className={styles.restated}>{e.understanding.restated}</p>
        <p>
          <strong>In and out:</strong> {e.understanding.inputs_outputs}
        </p>
        <div className={styles.twoCol}>
          <div>
            <h4>What to notice</h4>
            <ul>
              {e.understanding.observations.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
          {e.understanding.edge_cases.length > 0 && (
            <div>
              <h4>Edge cases to handle</h4>
              <ul>
                {e.understanding.edge_cases.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className={styles.ladder} aria-label="Complexity of each approach">
        {e.approaches.map((a, i) => (
          <span key={a.name} className={styles.rung}>
            <span className={styles.rungLabel}>{stageLabel(i, n, a.is_brute)}</span>
            <code>{a.time}</code>
            {i < n - 1 && (
              <span className={styles.rungArrow} aria-hidden="true">
                →
              </span>
            )}
          </span>
        ))}
      </div>

      <ol className={styles.steps}>
        {e.approaches.map((a, i) => {
          const label = stageLabel(i, n, a.is_brute);
          const last = i === n - 1;
          const primer = a.data_structure ? primerFor(a.data_structure.name) : null;
          return (
            <li key={a.name} className={styles.step}>
              <div className={styles.stepHead}>
                <span className={label === "Optimal" ? styles.badgeOptimal : styles.badge}>
                  {i + 2} · {label}
                </span>
                <h3>{a.name}</h3>
                <span className={styles.cx}>
                  Time <code>{a.time}</code> · Space <code>{a.space}</code>
                </span>
              </div>
              <p className={styles.intuition}>{a.intuition}</p>
              {a.data_structure && (
                <div className={styles.ds}>
                  <p>
                    <span className={styles.dsName}>{a.data_structure.name}</span> {a.data_structure.why}
                  </p>
                  {primer && (
                    <Link to={primer.href} className={styles.dsLink}>
                      See how {primer.what} works, hands-on →
                    </Link>
                  )}
                </div>
              )}
              <h4>Step by step</h4>
              <ol className={styles.plan}>
                {a.steps.map((s, k) => (
                  <li key={k}>{s}</li>
                ))}
              </ol>
              <p className={styles.why}>
                <strong>Why {a.time}:</strong> {a.complexity_reasoning}
              </p>
              {a.bottleneck && (
                <p className={last ? styles.enough : styles.bottleneck}>
                  <strong>{last ? "Why this is good enough: " : "The bottleneck: "}</strong>
                  {a.bottleneck}
                  {!last && <span className={styles.next}> So the next idea is to remove that waste.</span>}
                </p>
              )}
            </li>
          );
        })}
      </ol>

      <div className={styles.remember}>
        <p className={styles.pattern}>
          Pattern: <strong>{e.pattern}</strong>
        </p>
        <p>{e.takeaway}</p>
      </div>
    </section>
  );
}
