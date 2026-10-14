Given tasks and "this must come before that" rules, put the tasks in an order that respects every rule. As a graph, each rule is a directed edge `u → v`, and the graph has no cycles (otherwise no order exists).

Kahn's algorithm counts, for every node, how many edges point into it: its *indegree*. A node with indegree 0 has nothing that must come before it, so it can go next. Taking it removes its outgoing edges, which lowers its neighbours' indegrees; any that reach 0 become ready too. Repeat until nothing is ready.

Many orders can be valid. This version keeps the ready nodes in a min-heap and always takes the smallest, which gives the one order that is smallest when compared position by position. It takes O((n + m) log n) time for n nodes and m edges, or O(n + m) with a plain queue when any valid order will do.
