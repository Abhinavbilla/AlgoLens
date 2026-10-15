// The beginner path: an order to learn in, each stage building on the last. Items are library
// slugs or primers ("primer:<id>"); library slugs that aren't in the library yet are skipped.

export type Stage = { title: string; why: string; items: string[] };

export const PRIMERS: Record<string, { title: string; summary: string }> = {
  arrays: {
    title: "Arrays and indexes",
    summary: "Boxes in a row, numbered from 0. Everything else is built on this.",
  },
  "big-o": {
    title: "Big-O: how work grows",
    summary: "Why one solution finishes instantly and another never does.",
  },
  recursion: {
    title: "Recursion and the call stack",
    summary: "A function that calls itself, and how the computer keeps track.",
  },
};

export const PATH: Stage[] = [
  {
    title: "Foundations",
    why: "Three ideas every later topic leans on. Ten minutes here saves hours later.",
    items: ["primer:arrays", "primer:big-o", "primer:recursion"],
  },
  {
    title: "Your first algorithms",
    why: "Simple loops over an array, so you get used to reading code step by step.",
    items: ["bubble-sort", "insertion-sort", "binary-search"],
  },
  {
    title: "Array patterns",
    why: "The patterns behind a large share of easy and medium interview questions.",
    items: ["two-pointers", "sliding-window", "prefix-sums", "hash-map-counting"],
  },
  {
    title: "Recursion in action",
    why: "Split a problem, solve the pieces, combine. Watch the call stack grow and shrink.",
    items: ["merge-sort", "quick-sort", "subsets", "permutations"],
  },
  {
    title: "Stacks and heaps",
    why: "Structures that remember the right thing at the right time.",
    items: ["monotonic-stack", "heap-operations"],
  },
  {
    title: "Linked lists and trees",
    why: "Nodes that point to other nodes: the step from arrays to real data structures.",
    items: [
      "reverse-linked-list",
      "fast-slow-pointers",
      "preorder-traversal",
      "inorder-traversal",
      "postorder-traversal",
      "level-order",
      "bst-insert-search",
    ],
  },
  {
    title: "Graphs",
    why: "Maps, networks and dependencies: exploring everything that's connected.",
    items: ["grid-bfs", "graph-dfs", "topological-sort", "union-find", "dijkstra"],
  },
  {
    title: "Dynamic programming and greedy",
    why: "Answer big questions by reusing small answers, or by always taking the best next step.",
    items: ["house-robber", "coin-change", "knapsack", "lcs", "merge-intervals"],
  },
  {
    title: "Going further",
    why: "For when the basics feel easy.",
    items: ["segment-tree"],
  },
];
