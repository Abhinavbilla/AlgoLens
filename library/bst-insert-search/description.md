A binary search tree keeps one rule at every node: everything in its left subtree is smaller, and everything in its right subtree is not smaller. That rule turns the tree into a decision path.

**Insert** walks down from the root. At each node it goes left if the new value is smaller and right otherwise, until it falls off the tree, and the new node goes there. **Search** walks the same way: compare with the node, go left or right, and stop when you find the value or run out of tree.

Each step discards a whole subtree, so on a reasonably balanced tree both take O(log n) time, the same idea as binary search on a sorted array. Insert values already in sorted order, though, and the tree becomes a single long chain, where everything is O(n). That's why real libraries use self-balancing trees.
