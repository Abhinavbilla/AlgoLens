def dfs_order(n, edges, source):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    visited = [False] * n
    order = []

    def visit(u):
        visited[u] = True
        order.append(u)
        for v in adj[u]:
            if not visited[v]:
                visit(v)

    visit(source)
    return order
