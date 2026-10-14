A pre-order traversal visits a node *before* anything below it: record the node, then traverse its left subtree, then its right subtree. Recursion does the bookkeeping: each call handles one node, and the call stack remembers where to return to.

Pre-order lists a parent before its children, so it's the natural order for copying a tree or writing it out so it can be rebuilt. Every node is visited once, so it takes O(n) time, plus O(h) space for the call stack, where h is the tree's height.
