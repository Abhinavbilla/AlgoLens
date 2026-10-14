Depth-first search explores a graph by going as deep as it can before backing up. From a node, it moves to the first neighbour it hasn't visited yet, and from there to *that* node's first unvisited neighbour, and so on. Only when a node has no unvisited neighbours left does it go back to the previous node and try its next neighbour.

Recursion makes this natural: `visit(u)` marks `u`, then calls `visit` on each unvisited neighbour in turn. The call stack holds the path from the start to the current node, which is exactly the trail DFS backs up along. Marking a node *before* exploring from it is what stops cycles from looping forever.

Each node is visited once and each edge is looked at twice (once from each end), so it takes O(n + m) time for n nodes and m edges, and O(n) space. DFS is the building block for finding connected components, detecting cycles and topological sorting. Nodes that can't be reached from the start are never visited.
