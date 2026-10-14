A level-order traversal visits a binary tree one level at a time: the root, then its children, then their children, and so on. It's breadth-first search on a tree.

A queue keeps the order right. At the start of each level, the queue holds exactly that level's nodes, so the loop takes that many from the front. Each node it takes adds its children to the back, ready for the next level. Every node goes through the queue once, so this takes O(n) time.
