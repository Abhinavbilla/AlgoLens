import { useState } from "react";
import styles from "./demos.module.css";

// Small hands-on widgets for the primers. Each one is driven by buttons (keyboard and screen
// reader friendly) and says in words what just happened.

function Said({ text }: { text: string }) {
  return (
    <p className={styles.said} role="status">
      {text}
    </p>
  );
}

/* --- stacks and queues ------------------------------------------------------------------- */

export function StackQueueDemo() {
  const [next, setNext] = useState(4);
  const [stack, setStack] = useState([1, 2, 3]);
  const [queue, setQueue] = useState([1, 2, 3]);
  const [said, setSaid] = useState("Both hold 1, 2, 3, added in that order. Try taking one out of each.");

  const add = () => {
    setStack((s) => [...s, next]);
    setQueue((q) => [...q, next]);
    setSaid(`Added ${next} to both. In the stack it lands on top; in the queue it joins the back.`);
    setNext(next + 1);
  };
  const take = () => {
    if (stack.length === 0) {
      setSaid("Both are empty. Add something first.");
      return;
    }
    const top = stack[stack.length - 1];
    const front = queue[0];
    setStack((s) => s.slice(0, -1));
    setQueue((q) => q.slice(1));
    setSaid(`The stack gave back ${top}, the last one in. The queue gave back ${front}, the first one in.`);
  };

  return (
    <div className={styles.demo}>
      <div className={styles.twoUp}>
        <figure className={styles.figure}>
          <figcaption>Stack: last in, first out</figcaption>
          <ol className={styles.stack} aria-label={`Stack, bottom to top: ${stack.join(", ") || "empty"}`}>
            {stack.map((v, i) => (
              <li key={i} className={i === stack.length - 1 ? styles.hot : undefined}>
                {v}
                {i === stack.length - 1 && <span className={styles.tag}>top</span>}
              </li>
            ))}
            {stack.length === 0 && <li className={styles.empty}>empty</li>}
          </ol>
        </figure>
        <figure className={styles.figure}>
          <figcaption>Queue: first in, first out</figcaption>
          <ol className={styles.queue} aria-label={`Queue, front to back: ${queue.join(", ") || "empty"}`}>
            {queue.map((v, i) => (
              <li key={i} className={i === 0 ? styles.hot : undefined}>
                {v}
                {i === 0 && <span className={styles.tag}>front</span>}
              </li>
            ))}
            {queue.length === 0 && <li className={styles.empty}>empty</li>}
          </ol>
        </figure>
      </div>
      <div className={styles.buttons}>
        <button type="button" onClick={add} disabled={stack.length >= 7}>
          Add {next} to both
        </button>
        <button type="button" onClick={take}>
          Take one out of each
        </button>
      </div>
      <Said text={said} />
    </div>
  );
}

/* --- hash maps --------------------------------------------------------------------------- */

const BUCKETS = 7;

export function hashOf(word: string): { codes: number[]; sum: number; bucket: number } {
  const codes = [...word].map((c) => c.charCodeAt(0));
  const sum = codes.reduce((a, b) => a + b, 0);
  return { codes, sum, bucket: sum % BUCKETS };
}

export function HashDemo() {
  const [table, setTable] = useState<string[][]>(() => {
    const t: string[][] = Array.from({ length: BUCKETS }, () => []);
    for (const w of ["cat", "dog", "owl"]) t[hashOf(w).bucket].push(w);
    return t;
  });
  const [word, setWord] = useState("bee");
  const [last, setLast] = useState<number | null>(null);
  const [said, setSaid] = useState("Type a word and store it. Watch where it lands.");
  const clean = word.trim().toLowerCase().slice(0, 12);
  const h = clean ? hashOf(clean) : null;

  const store = () => {
    if (!h) return;
    const already = table[h.bucket].includes(clean);
    const crowded = table[h.bucket].length > 0 && !already;
    setTable((t) => t.map((b, i) => (i === h.bucket && !already ? [...b, clean] : b)));
    setLast(h.bucket);
    setSaid(
      already
        ? `"${clean}" is already in bucket ${h.bucket}. Finding it took one jump, no searching.`
        : crowded
          ? `"${clean}" landed in bucket ${h.bucket}, which already had a word: a collision. They share the bucket as a short list.`
          : `"${clean}" went straight into bucket ${h.bucket}. To find it later, compute the same number again and jump there.`,
    );
  };

  return (
    <div className={styles.demo}>
      <div className={styles.hashInput}>
        <label>
          Word{" "}
          <input value={word} maxLength={12} onChange={(e) => setWord(e.target.value)} spellCheck={false} />
        </label>
        <button type="button" onClick={store} disabled={!h}>
          Store it
        </button>
      </div>
      {h && (
        <p className={styles.formula}>
          letter codes {h.codes.join(" + ")} = {h.sum}; {h.sum} mod {BUCKETS} ={" "}
          <strong>bucket {h.bucket}</strong>
        </p>
      )}
      <ol className={styles.buckets} aria-label="Hash table buckets">
        {table.map((words, i) => (
          <li key={i} className={i === last ? styles.hot : undefined}>
            <span className={styles.bucketNo}>{i}</span>
            <span className={styles.bucketWords}>{words.length ? words.join(" → ") : "·"}</span>
          </li>
        ))}
      </ol>
      <Said text={said} />
    </div>
  );
}

/* --- linked lists ------------------------------------------------------------------------ */

export function LinkedListDemo() {
  const [nodes, setNodes] = useState([7, 3, 9]);
  const [next, setNext] = useState(5);
  const [said, setSaid] = useState("A chain of nodes. Each one only knows the node after it.");
  const steps = nodes.length;

  return (
    <div className={styles.demo}>
      <ol className={styles.chain} aria-label={`Linked list: ${nodes.join(" then ") || "empty"}`}>
        <li className={styles.headLabel} aria-hidden="true">
          head →
        </li>
        {nodes.map((v, i) => (
          <li key={`${i}-${v}`} className={i === 0 ? styles.hot : undefined}>
            <span className={styles.node}>{v}</span>
            <span className={styles.arrow} aria-hidden="true">
              →
            </span>
          </li>
        ))}
        <li className={styles.nullNode}>null</li>
      </ol>
      <div className={styles.buttons}>
        <button
          type="button"
          disabled={nodes.length >= 7}
          onClick={() => {
            setNodes([next, ...nodes]);
            setSaid(`Added ${next} at the front: one new node, one arrow changed. Nothing else moved.`);
            setNext(next + 1);
          }}
        >
          Add {next} at the front
        </button>
        <button
          type="button"
          disabled={nodes.length === 0}
          onClick={() => {
            setSaid(`Removed ${nodes[0]}: head now points at the next node.`);
            setNodes(nodes.slice(1));
          }}
        >
          Remove the front node
        </button>
        <button
          type="button"
          disabled={nodes.length === 0}
          onClick={() =>
            setSaid(
              `To reach the last node (${nodes[nodes.length - 1]}) you must follow ${steps} arrow${steps === 1 ? "" : "s"} from the head, one at a time. An array would jump straight there.`,
            )
          }
        >
          Find the last node
        </button>
      </div>
      <Said text={said} />
    </div>
  );
}

/* --- trees ------------------------------------------------------------------------------- */

type TNode = { id: string; v: number; x: number; y: number; parent?: string; role: string };
const TREE: TNode[] = [
  { id: "a", v: 8, x: 200, y: 36, role: "the root: the only node with no parent. Depth 0." },
  { id: "b", v: 3, x: 110, y: 106, parent: "a", role: "a child of 8, and the parent of 1 and 6. Depth 1." },
  { id: "c", v: 10, x: 290, y: 106, parent: "a", role: "a child of 8 and the parent of 14. Depth 1." },
  { id: "d", v: 1, x: 60, y: 176, parent: "b", role: "a leaf: it has no children. Depth 2." },
  { id: "e", v: 6, x: 160, y: 176, parent: "b", role: "a leaf, and the right child of 3. Depth 2." },
  { id: "f", v: 14, x: 340, y: 176, parent: "c", role: "a leaf, and the right child of 10. Depth 2." },
];

export function TreeDemo() {
  const [picked, setPicked] = useState<TNode | null>(null);
  const byId = new Map(TREE.map((n) => [n.id, n]));
  return (
    <div className={styles.demo}>
      <svg viewBox="0 0 400 214" className={styles.treeSvg} role="img" aria-label="A binary tree with root 8">
        {TREE.filter((n) => n.parent).map((n) => {
          const p = byId.get(n.parent!)!;
          return <line key={n.id} x1={p.x} y1={p.y} x2={n.x} y2={n.y} />;
        })}
        {TREE.map((n) => (
          <g key={n.id} className={picked?.id === n.id ? styles.svgHot : undefined}>
            <circle cx={n.x} cy={n.y} r={20} />
            <text x={n.x} y={n.y}>
              {n.v}
            </text>
          </g>
        ))}
      </svg>
      <div className={styles.buttons}>
        {TREE.map((n) => (
          <button key={n.id} type="button" aria-pressed={picked?.id === n.id} onClick={() => setPicked(n)}>
            {n.v}
          </button>
        ))}
      </div>
      <Said text={picked ? `${picked.v} is ${picked.role}` : "Pick a node to see what it's called."} />
    </div>
  );
}

/* --- graphs ------------------------------------------------------------------------------ */

const G_NODES = [
  { id: 0, x: 60, y: 60 },
  { id: 1, x: 200, y: 36 },
  { id: 2, x: 330, y: 80 },
  { id: 3, x: 110, y: 180 },
  { id: 4, x: 270, y: 186 },
];
const G_EDGES: [number, number][] = [
  [0, 1],
  [0, 3],
  [1, 2],
  [1, 4],
  [3, 4],
];

export function adjacency(n: number, edges: [number, number][]): number[][] {
  const adj: number[][] = Array.from({ length: n }, () => []);
  for (const [a, b] of edges) {
    adj[a].push(b);
    adj[b].push(a);
  }
  return adj.map((l) => l.sort((a, b) => a - b));
}

const listOf = (xs: number[]) =>
  xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;

export function GraphDemo() {
  const adj = adjacency(G_NODES.length, G_EDGES);
  const [picked, setPicked] = useState<number | null>(null);
  const near = (id: number) => picked !== null && adj[picked].includes(id);
  return (
    <div className={styles.demo}>
      <div className={styles.twoUp}>
        <svg
          viewBox="0 0 390 220"
          className={styles.treeSvg}
          role="img"
          aria-label="A graph with 5 nodes and 5 edges"
        >
          {G_EDGES.map(([a, b]) => (
            <line
              key={`${a}-${b}`}
              x1={G_NODES[a].x}
              y1={G_NODES[a].y}
              x2={G_NODES[b].x}
              y2={G_NODES[b].y}
              className={picked !== null && (a === picked || b === picked) ? styles.edgeHot : undefined}
            />
          ))}
          {G_NODES.map((n) => (
            <g
              key={n.id}
              className={n.id === picked ? styles.svgHot : near(n.id) ? styles.svgNear : undefined}
            >
              <circle cx={n.x} cy={n.y} r={20} />
              <text x={n.x} y={n.y}>
                {n.id}
              </text>
            </g>
          ))}
        </svg>
        <table className={styles.adj}>
          <caption>Adjacency list: each node's neighbours</caption>
          <tbody>
            {adj.map((list, i) => (
              <tr key={i} className={i === picked ? styles.hot : undefined}>
                <th scope="row">
                  <button type="button" aria-pressed={i === picked} onClick={() => setPicked(i)}>
                    {i}
                  </button>
                </th>
                <td>{list.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Said
        text={
          picked === null
            ? "Pick a node in the table to light up its neighbours in the picture."
            : `Node ${picked} is connected to ${listOf(adj[picked])}. That row of the table is all the program stores about it.`
        }
      />
    </div>
  );
}
