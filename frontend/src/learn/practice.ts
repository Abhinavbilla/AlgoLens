// "Practice next": hand-picked problems on other sites that use the same idea as a library
// entry, easiest first. Links only; we never copy problem statements.

export type Practice = {
  title: string;
  url: string;
  level: "Easy" | "Medium" | "Hard";
  site: "LeetCode" | "Codeforces";
};

const lc = (title: string, slug: string, level: Practice["level"]): Practice => ({
  title,
  url: `https://leetcode.com/problems/${slug}/`,
  level,
  site: "LeetCode",
});

const SORTING = [
  lc("Merge Sorted Array", "merge-sorted-array", "Easy"),
  lc("Sort Colors", "sort-colors", "Medium"),
  lc("Sort an Array", "sort-an-array", "Medium"),
];

export const PRACTICE: Record<string, Practice[]> = {
  "bubble-sort": SORTING,
  "insertion-sort": [...SORTING, lc("Insertion Sort List", "insertion-sort-list", "Medium")],
  "merge-sort": [
    lc("Merge Sorted Array", "merge-sorted-array", "Easy"),
    lc("Sort an Array", "sort-an-array", "Medium"),
    lc("Sort List", "sort-list", "Medium"),
  ],
  "quick-sort": [
    lc("Sort Colors", "sort-colors", "Medium"),
    lc("Sort an Array", "sort-an-array", "Medium"),
    lc("Kth Largest Element in an Array", "kth-largest-element-in-an-array", "Medium"),
  ],
  "binary-search": [
    lc("Binary Search", "binary-search", "Easy"),
    lc("Search Insert Position", "search-insert-position", "Easy"),
    lc("First Bad Version", "first-bad-version", "Easy"),
    lc(
      "Find First and Last Position of Element in Sorted Array",
      "find-first-and-last-position-of-element-in-sorted-array",
      "Medium",
    ),
    lc("Search in Rotated Sorted Array", "search-in-rotated-sorted-array", "Medium"),
  ],
  "two-pointers": [
    lc("Valid Palindrome", "valid-palindrome", "Easy"),
    lc("Two Sum II - Input Array Is Sorted", "two-sum-ii-input-array-is-sorted", "Medium"),
    lc("Container With Most Water", "container-with-most-water", "Medium"),
    lc("3Sum", "3sum", "Medium"),
  ],
  "sliding-window": [
    lc("Maximum Average Subarray I", "maximum-average-subarray-i", "Easy"),
    lc("Minimum Size Subarray Sum", "minimum-size-subarray-sum", "Medium"),
    lc(
      "Longest Substring Without Repeating Characters",
      "longest-substring-without-repeating-characters",
      "Medium",
    ),
    {
      title: "Books (279B)",
      url: "https://codeforces.com/problemset/problem/279/B",
      level: "Medium",
      site: "Codeforces",
    },
  ],
  "prefix-sums": [
    lc("Running Sum of 1d Array", "running-sum-of-1d-array", "Easy"),
    lc("Range Sum Query - Immutable", "range-sum-query-immutable", "Easy"),
    lc("Product of Array Except Self", "product-of-array-except-self", "Medium"),
    lc("Subarray Sum Equals K", "subarray-sum-equals-k", "Medium"),
  ],
  "monotonic-stack": [
    lc("Next Greater Element I", "next-greater-element-i", "Easy"),
    lc("Daily Temperatures", "daily-temperatures", "Medium"),
    lc("Largest Rectangle in Histogram", "largest-rectangle-in-histogram", "Hard"),
  ],
  "heap-operations": [
    lc("Last Stone Weight", "last-stone-weight", "Easy"),
    lc("Kth Largest Element in a Stream", "kth-largest-element-in-a-stream", "Easy"),
    lc("Top K Frequent Elements", "top-k-frequent-elements", "Medium"),
    lc("Merge k Sorted Lists", "merge-k-sorted-lists", "Hard"),
  ],
  "grid-bfs": [
    lc("Flood Fill", "flood-fill", "Easy"),
    lc("Number of Islands", "number-of-islands", "Medium"),
    lc("Rotting Oranges", "rotting-oranges", "Medium"),
    lc("Shortest Path in Binary Matrix", "shortest-path-in-binary-matrix", "Medium"),
  ],
  "graph-dfs": [
    lc("Find if Path Exists in Graph", "find-if-path-exists-in-graph", "Easy"),
    lc("Number of Provinces", "number-of-provinces", "Medium"),
    lc("Clone Graph", "clone-graph", "Medium"),
  ],
  dijkstra: [
    lc("Network Delay Time", "network-delay-time", "Medium"),
    lc("Path With Minimum Effort", "path-with-minimum-effort", "Medium"),
    lc("Cheapest Flights Within K Stops", "cheapest-flights-within-k-stops", "Medium"),
  ],
  "topological-sort": [
    lc("Course Schedule", "course-schedule", "Medium"),
    lc("Course Schedule II", "course-schedule-ii", "Medium"),
  ],
  "union-find": [
    lc("Number of Provinces", "number-of-provinces", "Medium"),
    lc("Redundant Connection", "redundant-connection", "Medium"),
    lc("Accounts Merge", "accounts-merge", "Medium"),
  ],
  "level-order": [
    lc("Maximum Depth of Binary Tree", "maximum-depth-of-binary-tree", "Easy"),
    lc("Binary Tree Level Order Traversal", "binary-tree-level-order-traversal", "Medium"),
    lc("Binary Tree Right Side View", "binary-tree-right-side-view", "Medium"),
  ],
  "preorder-traversal": [
    lc("Binary Tree Preorder Traversal", "binary-tree-preorder-traversal", "Easy"),
    lc("Same Tree", "same-tree", "Easy"),
    lc("Invert Binary Tree", "invert-binary-tree", "Easy"),
  ],
  "inorder-traversal": [
    lc("Binary Tree Inorder Traversal", "binary-tree-inorder-traversal", "Easy"),
    lc("Validate Binary Search Tree", "validate-binary-search-tree", "Medium"),
    lc("Kth Smallest Element in a BST", "kth-smallest-element-in-a-bst", "Medium"),
  ],
  "postorder-traversal": [
    lc("Binary Tree Postorder Traversal", "binary-tree-postorder-traversal", "Easy"),
    lc("Diameter of Binary Tree", "diameter-of-binary-tree", "Easy"),
    lc("Balanced Binary Tree", "balanced-binary-tree", "Easy"),
  ],
  "house-robber": [
    lc("Climbing Stairs", "climbing-stairs", "Easy"),
    lc("Min Cost Climbing Stairs", "min-cost-climbing-stairs", "Easy"),
    lc("House Robber", "house-robber", "Medium"),
    lc("House Robber II", "house-robber-ii", "Medium"),
  ],
  lcs: [
    lc("Unique Paths", "unique-paths", "Medium"),
    lc("Longest Common Subsequence", "longest-common-subsequence", "Medium"),
    lc("Edit Distance", "edit-distance", "Medium"),
  ],
  knapsack: [
    lc("Partition Equal Subset Sum", "partition-equal-subset-sum", "Medium"),
    lc("Target Sum", "target-sum", "Medium"),
    lc("Last Stone Weight II", "last-stone-weight-ii", "Medium"),
  ],
  subsets: [
    lc("Subsets", "subsets", "Medium"),
    lc("Subsets II", "subsets-ii", "Medium"),
    lc("Combination Sum", "combination-sum", "Medium"),
  ],
  permutations: [
    lc("Letter Case Permutation", "letter-case-permutation", "Medium"),
    lc("Permutations", "permutations", "Medium"),
    lc("Permutations II", "permutations-ii", "Medium"),
  ],
  "segment-tree": [
    lc("Range Sum Query - Mutable", "range-sum-query-mutable", "Medium"),
    lc("Count of Smaller Numbers After Self", "count-of-smaller-numbers-after-self", "Hard"),
  ],
  "hash-map-counting": [
    lc("Contains Duplicate", "contains-duplicate", "Easy"),
    lc("Valid Anagram", "valid-anagram", "Easy"),
    lc("Two Sum", "two-sum", "Easy"),
    lc("Group Anagrams", "group-anagrams", "Medium"),
  ],
  "reverse-linked-list": [
    lc("Reverse Linked List", "reverse-linked-list", "Easy"),
    lc("Merge Two Sorted Lists", "merge-two-sorted-lists", "Easy"),
    lc("Reverse Linked List II", "reverse-linked-list-ii", "Medium"),
  ],
  "fast-slow-pointers": [
    lc("Middle of the Linked List", "middle-of-the-linked-list", "Easy"),
    lc("Linked List Cycle", "linked-list-cycle", "Easy"),
    lc("Happy Number", "happy-number", "Easy"),
    lc("Linked List Cycle II", "linked-list-cycle-ii", "Medium"),
  ],
  "bst-insert-search": [
    lc("Search in a Binary Search Tree", "search-in-a-binary-search-tree", "Easy"),
    lc("Insert into a Binary Search Tree", "insert-into-a-binary-search-tree", "Medium"),
    lc(
      "Lowest Common Ancestor of a Binary Search Tree",
      "lowest-common-ancestor-of-a-binary-search-tree",
      "Medium",
    ),
  ],
  "coin-change": [
    lc("Coin Change", "coin-change", "Medium"),
    lc("Coin Change II", "coin-change-ii", "Medium"),
    lc("Perfect Squares", "perfect-squares", "Medium"),
  ],
  "merge-intervals": [
    lc("Merge Intervals", "merge-intervals", "Medium"),
    lc("Insert Interval", "insert-interval", "Medium"),
    lc("Non-overlapping Intervals", "non-overlapping-intervals", "Medium"),
  ],
};
