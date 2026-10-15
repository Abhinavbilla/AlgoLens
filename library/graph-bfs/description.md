How many steps is every node from the start, if each edge is one step? Breadth-first search answers it by exploring in rings: first everything one step away, then everything two steps away, and so on.

A **queue** keeps that order. Start with just the source, at distance 0. Take the node at the front; every neighbour not reached yet is one step further than it, so record that distance and add the neighbour to the back of the queue. Because nodes leave the queue in order of distance, the first time you reach a node is always by a shortest route.

Each node and edge is handled once: O(n + m) time. BFS is the go-to for shortest paths when every step costs the same; when steps have different costs, Dijkstra takes over.
