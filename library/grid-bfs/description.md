Breadth-first search (BFS) explores a grid in rings: first every cell one step from the start, then every cell two steps away, and so on. A queue makes that happen. Cells are added to the back and taken from the front, so all the cells at distance *d* come out before any cell at distance *d + 1*.

The first time BFS reaches a cell is therefore by a shortest path. When it takes the goal from the front of the queue, its distance is the answer. Each cell enters the queue at most once, so this takes O(rows × columns) time.
