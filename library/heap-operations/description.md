A min-heap gives you the smallest of a changing set of values quickly. It's a binary tree stored in a plain array: the children of position `i` are at `2i + 1` and `2i + 2`, and its parent is at `(i - 1) // 2`. The one rule is that every parent is no bigger than its children, so the smallest value is always at position 0.

**Push** puts the new value at the end, then *sifts it up*: while it's smaller than its parent, swap the two. **Pop** takes the top value, moves the last value into the top spot, then *sifts it down*: while one of its children is smaller, swap it with the smaller child.

The tree is always as balanced as possible, so its height is about log₂ n and both operations take O(log n) time. Heaps power priority queues, Dijkstra's algorithm and heap sort. This entry runs a list of operations and returns the values in the order they were popped.
