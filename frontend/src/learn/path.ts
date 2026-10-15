// The beginner path: an order to learn in, each stage building on the last. Items are library
// slugs or primers ("primer:<id>"); library slugs that aren't in the library yet are skipped.

export type Stage = { title: string; why: string; items: string[]; icon: string };

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
  hashing: {
    title: "Hash maps",
    summary: "How a dictionary finds anything in one jump, instead of searching.",
  },
  "stacks-queues": {
    title: "Stacks and queues",
    summary: "Last in, first out versus first in, first out, and why both are useful.",
  },
  "linked-lists": {
    title: "Linked lists",
    summary: "Nodes joined by arrows: cheap to change at the front, slow to search.",
  },
  trees: {
    title: "Trees",
    summary: "Roots, children, leaves and depth: the vocabulary every tree problem uses.",
  },
  strings: {
    title: "Strings",
    summary: "Characters in a row: slicing, and why building strings can be slow.",
  },
  sets: {
    title: "Sets",
    summary: "Unique values with instant membership, union and intersection.",
  },
  bits: {
    title: "Bits and binary",
    summary: "Numbers as rows of switches, and the operators that flip them.",
  },
  numbers: {
    title: "Number basics",
    summary: "Remainders, digits and the powers of two every algorithm leans on.",
  },
  "stable-sorting": {
    title: "Stable sorting",
    summary: "What a sort does with ties, and when that matters.",
  },
  graphs: {
    title: "Graphs",
    summary: "Things and the connections between them, and how a program stores them.",
  },
};

export const PATH: Stage[] = [
  {
    title: "Foundations",
    icon: "foundations",
    why: "Three ideas every later topic leans on. Ten minutes here saves hours later.",
    items: ["primer:arrays", "primer:big-o", "primer:recursion"],
  },
  {
    title: "Your first algorithms",
    icon: "sorting",
    why: "Simple loops over an array, so you get used to reading code step by step.",
    items: [
      "bubble-sort",
      "selection-sort",
      "insertion-sort",
      "counting-sort",
      "primer:stable-sorting",
      "binary-search-exact",
      "binary-search",
      "integer-sqrt",
    ],
  },
  {
    title: "Strings, hashing and sets",
    icon: "strings-hashing",
    why: "Text, and the structures that find anything in a single step.",
    items: [
      "primer:strings",
      "valid-palindrome",
      "primer:hashing",
      "primer:sets",
      "hash-map-counting",
      "valid-anagram",
      "longest-unique-substring",
    ],
  },
  {
    title: "Array patterns",
    icon: "array-techniques",
    why: "Small ideas that turn slow nested loops into a single pass.",
    items: ["two-pointers", "sliding-window", "prefix-sums", "kadane", "dutch-flag", "majority-vote"],
  },
  {
    title: "Numbers and bits",
    icon: "bits",
    why: "Remainders, digits and binary: the maths behind many tricks.",
    items: ["primer:numbers", "primer:bits", "count-bits"],
  },
  {
    title: "Recursion in action",
    icon: "recursion",
    why: "Split a problem, solve the pieces, combine. Watch the call stack grow and shrink.",
    items: ["merge-sort", "quick-sort", "subsets", "combinations", "permutations"],
  },
  {
    title: "Stacks, queues and heaps",
    icon: "stacks",
    why: "Structures that hand things back in a particular order.",
    items: ["primer:stacks-queues", "valid-parentheses", "monotonic-stack", "heap-operations", "k-largest"],
  },
  {
    title: "Linked lists",
    icon: "linked-lists",
    why: "Your first data structure built from nodes and pointers instead of a row of boxes.",
    items: ["primer:linked-lists", "reverse-linked-list", "fast-slow-pointers", "merge-sorted-lists"],
  },
  {
    title: "Trees",
    icon: "trees",
    why: "Nodes with children: the shape behind file systems, search trees and heaps.",
    items: [
      "primer:trees",
      "tree-depth",
      "preorder-traversal",
      "inorder-traversal",
      "postorder-traversal",
      "level-order",
      "bst-insert-search",
    ],
  },
  {
    title: "Graphs",
    icon: "graphs",
    why: "Maps, networks and dependencies: exploring everything that's connected.",
    items: [
      "primer:graphs",
      "graph-bfs",
      "grid-bfs",
      "graph-dfs",
      "topological-sort",
      "union-find",
      "dijkstra",
    ],
  },
  {
    title: "Dynamic programming and greedy",
    icon: "dynamic-programming",
    why: "Answer big questions by reusing small answers, or by always taking the best next step.",
    items: [
      "climbing-stairs",
      "house-robber",
      "coin-change",
      "lis",
      "knapsack",
      "lcs",
      "jump-game",
      "merge-intervals",
    ],
  },
  {
    title: "Going further",
    icon: "range-queries",
    why: "For when the basics feel easy.",
    items: ["segment-tree"],
  },
];
