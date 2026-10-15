import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { GraphDemo, HashDemo, LinkedListDemo, StackQueueDemo, TreeDemo } from "./demos";
import { PATH, PRIMERS } from "./path";
import styles from "./learn.module.css";
import { useProgress } from "./progress";

export function PrimerPage() {
  const { topic = "" } = useParams();
  const primer = PRIMERS[topic];
  const body = BODIES[topic];
  const { done, toggle } = useProgress();
  if (!primer || !body) {
    return (
      <section className={styles.page}>
        <h1>No such primer</h1>
        <Link to="/path">Back to the learning path</Link>
      </section>
    );
  }
  const id = `primer:${topic}`;
  const order = PATH.flatMap((s) => s.items);
  const next = order[order.indexOf(id) + 1];
  const nextHref = next?.startsWith("primer:")
    ? `/learn/${next.slice(7)}`
    : next
      ? `/library/${next}`
      : "/path";
  const isDone = done.has(id);

  return (
    <article className={styles.primer}>
      <p className={styles.crumbs}>
        <Link to="/path">Learning path</Link> / {PATH.find((s) => s.items.includes(id))?.title ?? "Primers"}
      </p>
      <p className={styles.eyebrow}>Primer</p>
      <h1>{primer.title}</h1>
      <p className={styles.lead}>{primer.summary}</p>
      {body}
      <footer className={styles.primerFoot}>
        <button
          type="button"
          className={isDone ? styles.doneButtonOn : styles.doneButton}
          aria-pressed={isDone}
          onClick={() => toggle(id)}
        >
          {isDone ? "✓ Marked as done" : "Mark as done"}
        </button>
        <Link to={nextHref} className={styles.nextLink}>
          Next on the path →
        </Link>
      </footer>
    </article>
  );
}

function Check({ question, answer }: { question: ReactNode; answer: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <aside className={styles.check} aria-label="Check yourself">
      <p className={styles.checkLabel}>Check yourself</p>
      <p>{question}</p>
      {open ? (
        <p className={styles.checkAnswer}>{answer}</p>
      ) : (
        <button type="button" onClick={() => setOpen(true)}>
          Show the answer
        </button>
      )}
    </aside>
  );
}

const NUMS = [7, 3, 9, 1, 5, 8];

function Boxes({ highlight }: { highlight?: number }) {
  return (
    <ol className={styles.boxes} aria-label={`An array of ${NUMS.length} values`}>
      {NUMS.map((v, i) => (
        <li key={i} className={i === highlight ? styles.boxOn : undefined}>
          <span className={styles.boxIndex}>{i}</span>
          <span className={styles.boxValue}>{v}</span>
        </li>
      ))}
    </ol>
  );
}

const SIZES = [10, 100, 1_000, 100_000];
const GROWTH: [string, (n: number) => number][] = [
  ["O(1)", () => 1],
  ["O(log n)", (n) => Math.ceil(Math.log2(n))],
  ["O(n)", (n) => n],
  ["O(n log n)", (n) => Math.ceil(n * Math.log2(n))],
  ["O(n²)", (n) => n * n],
];
const fmt = new Intl.NumberFormat("en-US");

const BODIES: Record<string, ReactNode> = {
  arrays: (
    <div className={styles.prose}>
      <h2>A row of numbered boxes</h2>
      <p>
        An array (a <code>list</code> in Python, a <code>vector</code> in C++) keeps values side by side. Each
        box has an <strong>index</strong>, its position, and indexes start at <strong>0</strong>.
      </p>
      <Boxes highlight={2} />
      <p>
        Here <code>nums[2]</code> is <strong>9</strong>: the third box, because counting starts at 0. There
        are {NUMS.length} values, so the last index is <code>len(nums) - 1</code>, which is 5.
      </p>
      <h2>Why arrays are fast</h2>
      <p>
        The computer can jump straight to any index, so reading <code>nums[i]</code> takes the same tiny time
        whether the array has 6 values or 6 million. That's what algorithms like binary search exploit.
      </p>
      <h2>Walking through an array</h2>
      <pre className={styles.code}>
        <code>{`for i in range(len(nums)):\n    print(i, nums[i])`}</code>
      </pre>
      <p>
        This visits every box once, from index 0 to the last. Most algorithms in this library are clever
        variations on this loop: two indexes moving towards each other, a window sliding along, a running
        total.
      </p>
      <h2>The classic mistakes</h2>
      <ul>
        <li>
          <strong>Off by one:</strong> <code>nums[len(nums)]</code> doesn't exist; the last box is{" "}
          <code>len(nums) - 1</code>.
        </li>
        <li>
          <strong>Forgetting the empty array:</strong> with no values, even <code>nums[0]</code> fails.
        </li>
      </ul>
      <Check
        question={
          <>
            For <code>nums = [4, 8, 15, 16, 23]</code>, what is <code>nums[3]</code>, and what is the index of
            the last value?
          </>
        }
        answer={
          <>
            <code>nums[3]</code> is 16 (indexes 0, 1, 2, 3 hold 4, 8, 15, 16). There are 5 values, so the last
            index is 4.
          </>
        }
      />
    </div>
  ),
  "big-o": (
    <div className={styles.prose}>
      <h2>Count steps, not seconds</h2>
      <p>
        Big-O describes how the amount of work grows as the input grows. If you double the input, does the
        work stay the same, double, or quadruple? That tells you whether a solution survives a big input.
      </p>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption>Roughly how many steps for an input of size n</caption>
          <thead>
            <tr>
              <th scope="col">n</th>
              {GROWTH.map(([name]) => (
                <th scope="col" key={name}>
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SIZES.map((n) => (
              <tr key={n}>
                <th scope="row">{fmt.format(n)}</th>
                {GROWTH.map(([name, f]) => (
                  <td key={name}>{fmt.format(f(n))}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        At n = 100,000, an O(n log n) solution takes about 1.7 million steps: instant. An O(n²) one takes ten
        billion: minutes, or a "Time Limit Exceeded" on LeetCode.
      </p>
      <h2>Read it from the constraints</h2>
      <p>
        A computer does very roughly 100 million simple steps a second, so the input limits hint at the
        answer:
      </p>
      <ul>
        <li>n ≤ 20: trying every combination (2ⁿ) is fine.</li>
        <li>n ≤ 1,000: two nested loops (n²) is fine.</li>
        <li>n ≤ 100,000 or more: you need O(n log n) or O(n).</li>
      </ul>
      <h2>See it happen</h2>
      <p>
        Every animation here counts the lines it runs ("operations so far"). Run bubble sort on a short list,
        then a longer one, and watch the count. For problems you paste, the result page draws a chart of how
        each approach's work grows.
      </p>
      <Check
        question="A solution has two nested loops over the input, and the input can have 100,000 items. Will it be fast enough?"
        answer="No. Two nested loops are O(n²): about 10 billion steps here. Look for an O(n) or O(n log n) idea, such as sorting first, two pointers or a hash map."
      />
    </div>
  ),
  recursion: (
    <div className={styles.prose}>
      <h2>A function that calls itself</h2>
      <p>
        A recursive function solves a problem by solving a <strong>smaller</strong> version of the same
        problem, until it reaches a case so small the answer is obvious: the <strong>base case</strong>.
      </p>
      <pre className={styles.code}>
        <code>{`def fact(n):\n    if n == 1:          # base case\n        return 1\n    return n * fact(n - 1)   # smaller problem`}</code>
      </pre>
      <h2>The call stack</h2>
      <p>
        Each call waits for the one it made. The computer keeps the waiting calls on a stack, newest on top,
        each with its own <code>n</code>:
      </p>
      <ol className={styles.callStack} aria-label="Call stack while computing fact(3)">
        <li>
          <code>fact(1)</code> returns 1 <span>(base case, on top)</span>
        </li>
        <li>
          <code>fact(2)</code> waits, then returns 2 × 1 = 2
        </li>
        <li>
          <code>fact(3)</code> waits, then returns 3 × 2 = 6 <span>(the first call, at the bottom)</span>
        </li>
      </ol>
      <p>
        The calls go down to the base case, then the answers come back up. Every animation in this library
        shows this stack, so you can watch it grow and shrink.
      </p>
      <h2>The classic mistake</h2>
      <p>
        Without a base case, or with one that's never reached, the calls never stop and the program crashes
        with a "maximum recursion depth" or stack overflow error.
      </p>
      <Check
        question={
          <>
            How many calls of <code>fact</code> are waiting on the stack at the deepest point of{" "}
            <code>fact(4)</code>?
          </>
        }
        answer={
          <>
            Four: <code>fact(4)</code>, <code>fact(3)</code>, <code>fact(2)</code> and <code>fact(1)</code>.
            Then they return one by one, top first.
          </>
        }
      />
    </div>
  ),
  hashing: (
    <div className={styles.prose}>
      <h2>Finding things without searching</h2>
      <p>
        To check whether a word is in a list, you'd normally compare it with every item. A{" "}
        <strong>hash map</strong> skips the search. It turns the key into a number (its <em>hash</em>) and
        uses that number to pick a bucket. To find the key again, compute the same number and jump straight
        there.
      </p>
      <HashDemo />
      <h2>What to remember</h2>
      <ul>
        <li>
          Looking up, adding and removing take <strong>O(1)</strong> time on average, whatever the size.
        </li>
        <li>
          Two keys can land in the same bucket, a <strong>collision</strong>. The bucket keeps a short list,
          so it still works; a good hash function keeps those lists short.
        </li>
        <li>
          In Python it's <code>dict</code> and <code>set</code>; in C++ it's <code>unordered_map</code> and{" "}
          <code>unordered_set</code>.
        </li>
        <li>The trade: extra memory for speed. That trade solves a huge number of problems.</li>
      </ul>
      <Check
        question="You need to know whether any value in an array appears twice. What's the hash map idea?"
        answer="Walk the array once, putting each value in a set. If a value is already in the set when you reach it, it's a duplicate. That's O(n) instead of comparing every pair, O(n²)."
      />
    </div>
  ),
  "stacks-queues": (
    <div className={styles.prose}>
      <h2>Two ways to hand things back</h2>
      <p>
        A <strong>stack</strong> is a pile of plates: you add to the top and take from the top, so the last
        thing in is the first out. A <strong>queue</strong> is a line at a counter: you join at the back and
        leave from the front, so the first in is the first out.
      </p>
      <StackQueueDemo />
      <h2>Where you'll meet them</h2>
      <ul>
        <li>
          <strong>Stacks:</strong> undo buttons, matching brackets, the call stack itself, and the monotonic
          stack pattern.
        </li>
        <li>
          <strong>Queues:</strong> processing in arrival order, and breadth-first search, which explores
          nearest things first.
        </li>
        <li>
          In Python, a <code>list</code> with <code>append</code> and <code>pop</code> is a stack, and{" "}
          <code>collections.deque</code> with <code>append</code> and <code>popleft</code> is a queue. In C++:{" "}
          <code>stack</code>, <code>queue</code> and <code>deque</code>.
        </li>
      </ul>
      <Check
        question="You push 1, 2, 3 onto a stack, pop once, then push 4. What's on top?"
        answer="4. After popping, the stack holds 1, 2 (3 came off), then 4 goes on top."
      />
    </div>
  ),
  "linked-lists": (
    <div className={styles.prose}>
      <h2>A chain instead of a row</h2>
      <p>
        An array keeps values side by side. A <strong>linked list</strong> keeps each value in its own{" "}
        <em>node</em>, which also holds an arrow (<code>next</code>) to the following node. The list is just a
        pointer to the first node, the <strong>head</strong>, and the last node points at nothing (
        <code>null</code> / <code>None</code>).
      </p>
      <LinkedListDemo />
      <h2>The trade-offs</h2>
      <ul>
        <li>
          Adding or removing at the front is <strong>O(1)</strong>: change one or two arrows, move nothing.
        </li>
        <li>
          Reaching the k-th node is <strong>O(k)</strong>: you have to follow the arrows. There's no jumping
          to an index.
        </li>
        <li>
          The golden rule when rewiring: save <code>node.next</code> before you overwrite it, or you lose the
          rest of the list.
        </li>
      </ul>
      <Check
        question="A list has 1,000 nodes. How many arrows do you follow to read the 500th value?"
        answer="499: start at the head (the 1st node) and follow next 499 times. An array would read it in one step."
      />
    </div>
  ),
  trees: (
    <div className={styles.prose}>
      <h2>Nodes with children</h2>
      <p>
        A <strong>tree</strong> starts from one node, the <strong>root</strong>. Each node can have children,
        and every node except the root has exactly one parent. In a <strong>binary tree</strong>, each node
        has at most two children: left and right.
      </p>
      <TreeDemo />
      <h2>The words you'll keep hearing</h2>
      <ul>
        <li>
          <strong>Leaf:</strong> a node with no children.
        </li>
        <li>
          <strong>Depth:</strong> how many steps a node is from the root. The root is at depth 0.
        </li>
        <li>
          <strong>Height:</strong> the depth of the deepest leaf. This tree's height is 2.
        </li>
        <li>
          <strong>Subtree:</strong> any node together with everything below it. Most tree code is recursion on
          subtrees: solve the left one, solve the right one, combine.
        </li>
      </ul>
      <Check
        question="In the tree above, which nodes are leaves, and what is the depth of 6?"
        answer="The leaves are 1, 6 and 14 (no children). 6 is two steps below the root (8 → 3 → 6), so its depth is 2."
      />
    </div>
  ),
  graphs: (
    <div className={styles.prose}>
      <h2>Things and the connections between them</h2>
      <p>
        A <strong>graph</strong> is a set of <strong>nodes</strong> (cities, people, web pages) and{" "}
        <strong>edges</strong> connecting pairs of them (roads, friendships, links). Edges can be one-way (
        <em>directed</em>) and can carry a cost (<em>weighted</em>). Trees and grids are special graphs.
      </p>
      <GraphDemo />
      <h2>How a program stores a graph</h2>
      <p>
        Usually as an <strong>adjacency list</strong>: for every node, the list of its neighbours. Problems
        often hand you a list of edges like <code>[[0, 1], [1, 2]]</code>, and your first few lines build this
        list:
      </p>
      <pre className={styles.code}>
        <code>{`adj = [[] for _ in range(n)]\nfor a, b in edges:\n    adj[a].append(b)\n    adj[b].append(a)   # leave out for one-way edges`}</code>
      </pre>
      <p>
        From there, every graph algorithm in the library comes down to the same question: which neighbour do
        you visit next? Nearest first gives breadth-first search, deepest first gives depth-first search, and
        cheapest first gives Dijkstra.
      </p>
      <Check
        question="In the graph above, which nodes can you reach from node 2 in exactly two steps?"
        answer="Node 2's only neighbour is 1. From 1 you can go to 0 or 4 (or back to 2), so two steps from 2 reaches 0, 2 and 4."
      />
    </div>
  ),
};
