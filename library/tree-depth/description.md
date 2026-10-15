How many levels does a tree have? You could walk every path from the root to a leaf, but recursion makes it a one-liner: a tree's depth is one (for its root) plus the depth of its deeper subtree. An empty tree has depth 0, which is where the recursion stops.

Watch the call stack: `depth` goes all the way down the left side first, comes back up with an answer, then does the right side. Each node waits for both children to report before it can answer, the post-order pattern behind most tree problems.

Every node is visited once: O(n) time, and O(h) space for the call stack, where h is the tree's height.
