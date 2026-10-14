def reference(n, edges, source):
    # Bellman-Ford: relax every edge, in both directions, n times. No heap, no greedy choice.
    inf = float("inf")
    dist = [inf] * n
    dist[source] = 0
    for _ in range(n):
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
            if dist[v] + w < dist[u]:
                dist[u] = dist[v] + w
    return [d if d != inf else -1 for d in dist]
