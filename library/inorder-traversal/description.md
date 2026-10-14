An in-order traversal visits a node *between* its subtrees: traverse the left subtree, record the node, then traverse the right subtree.

For a binary search tree, where everything on the left is smaller and everything on the right is larger, in-order lists the values in sorted order. That makes it the standard way to check that a tree really is a valid search tree. It takes O(n) time and O(h) space for the call stack, where h is the tree's height.
