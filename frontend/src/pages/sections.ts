// How the library is organised on the home page. Each entry's `category` (from the library
// files) belongs to one section; a category we don't know yet lands in "More".

export type Section = { id: string; title: string; intro: string; categories: string[] };

export const SECTIONS: Section[] = [
  {
    id: "sorting",
    title: "Sorting",
    intro:
      "Four ways to put things in order, from the obvious to the clever. Watch where each one spends its effort.",
    categories: ["Sorting"],
  },
  {
    id: "searching",
    title: "Searching",
    intro: "Throw away half of what's left at every step, and a million items take twenty looks.",
    categories: ["Binary search"],
  },
  {
    id: "array-techniques",
    title: "Array techniques",
    intro:
      "Small patterns that turn a nested loop into one pass: pointers moving inward, a window that slides, totals you compute once.",
    categories: ["Two pointers", "Sliding window", "Prefix sums", "Monotonic stack"],
  },
  {
    id: "heaps",
    title: "Heaps",
    intro: "Always know the smallest item, even while items keep arriving.",
    categories: ["Heaps"],
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
