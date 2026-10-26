// How the library is organised on the home page. Each entry's `category` (from the library
// files) belongs to one section; a category we don't know yet lands in "More".

export type Section = { id: string; title: string; intro: string; categories: string[] };

export const SECTIONS: Section[] = [
  {
    id: "sorting",
    title: "Sorting",
    intro:
      "Six ways to put things in order, from the obvious to the clever: simple loops, counting, and the divide-and-conquer classics merge sort and quick sort. Watch where each one spends its effort.",
    categories: ["Sorting"],
  },
  {
    id: "searching",
    title: "Searching",
    intro: "Throw away half of what's left at every step, and a million items take twenty looks.",
    categories: ["Binary search"],
  },
  {
    id: "strings-hashing",
    title: "Strings and hashing",
    intro: "Text, counting, and finding anything in one step with a hash map.",
    categories: ["Strings", "Hashing"],
  },
  {
    id: "bits",
    title: "Bits",
    intro: "Numbers as rows of switches, and tricks that flip them in one operation.",
    categories: ["Bit manipulation"],
  },
  {
    id: "array-techniques",
    title: "Array techniques",
    intro:
      "Small patterns that turn a nested loop into one pass: pointers moving inward, a window that slides, totals you compute once.",
    categories: ["Two pointers", "Sliding window", "Prefix sums", "Arrays"],
  },
  {
    id: "stacks",
    title: "Stacks and queues",
    intro:
      "Last in, first out: matching brackets, undo buttons, and the stack trick that finds the next bigger value.",
    categories: ["Stacks", "Monotonic stack"],
  },
  {
    id: "heaps",
    title: "Heaps",
    intro: "Always know the smallest item, even while items keep arriving.",
    categories: ["Heaps"],
  },
  {
    id: "linked-lists",
    title: "Linked lists",
    intro: "Nodes joined by arrows. Most of the trick is never losing track of the next node.",
    categories: ["Linked lists"],
  },
  {
    id: "graphs",
    title: "Graphs and grids",
    intro: "Exploring connections: breadth first, depth first, cheapest first, dependencies first.",
    categories: ["Graphs and grids"],
  },
  {
    id: "trees",
    title: "Trees",
    intro: "One structure, four orders of visiting it, and why each order is useful.",
    categories: ["Binary trees"],
  },
  {
    id: "dynamic-programming",
    title: "Dynamic programming",
    intro: "Solve each small question once, write the answer down, and build the big answer out of them.",
    categories: ["Dynamic programming"],
  },
  {
    id: "greedy",
    title: "Greedy",
    intro: "Take the obvious best step and never look back, once sorting has made that safe.",
    categories: ["Greedy"],
  },
  {
    id: "backtracking",
    title: "Backtracking",
    intro:
      "Try a choice, explore everything it leads to, undo it, try the next. The call stack tells the story.",
    categories: ["Backtracking"],
  },
  {
    id: "range-queries",
    title: "Range queries",
    intro: "Answer questions about any slice of an array without re-adding it every time.",
    categories: ["Segment trees"],
  },
];

export function sectionFor(category: string): string {
  return SECTIONS.find((s) => s.categories.includes(category))?.id ?? "more";
}
