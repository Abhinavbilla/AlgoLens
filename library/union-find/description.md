Union-find (also called a disjoint-set union) keeps track of which nodes are connected as edges arrive one at a time. Here it counts the connected groups.

Every group has a *leader*. Each node stores a `parent`; following parents upward always ends at the group's leader, which is its own parent. `find(x)` walks up to the leader. Two nodes are in the same group exactly when they have the same leader. To join two groups, point one leader at the other.

Two tricks keep the trees flat. *Union by size* always hangs the smaller group under the larger one's leader, so paths stay short. *Path halving* points each node visited by `find` at its grandparent, so later searches are shorter still. Together they make each operation take nearly constant time, O(α(n)), where α grows so slowly it's below 5 for any practical n. Counting groups is then just starting with n and subtracting one for every edge that joins two different groups.
