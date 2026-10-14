def reference(n, edges, source):
    # Iterative, with a stack of neighbour iterators that mirrors the recursion exactly.
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen = {source}
    order = [source]
    stack = [iter(adj[source])]
    while stack:
        for v in stack[-1]:
            if v not in seen:
                seen.add(v)
                order.append(v)
                stack.append(iter(adj[v]))
                break
        else:
            stack.pop()
    return order
