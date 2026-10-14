A segment tree answers range questions, here "what's the sum of positions `l` to `r`?", in O(log n) time each, and unlike prefix sums it can also absorb changes to single values in O(log n).

Each node of the tree covers a range of positions and stores that range's sum. The root (node 1) covers everything; a node covering `lo` to `hi` splits at `mid`, and its children 2·node and 2·node + 1 cover the two halves. Leaves cover single positions. The tree lives in a flat array of size 4n, which is always enough.

**Build** fills the leaves from the array and every other node as the sum of its two children: O(n). **Query** starts at the root. A node entirely outside the query range adds nothing; a node entirely inside adds its stored sum without looking deeper; anything partly inside asks both children. Only O(log n) nodes are ever partly inside, so each query is O(log n).
