def reference(n, edges, source):
    # Relax every edge n times (slow but simple): shortest step counts without a queue.
    dist = [-1] * n
    dist[source] = 0
    for _ in range(n):
        for a, b in edges:
            for x, y in ((a, b), (b, a)):
                if dist[x] != -1 and (dist[y] == -1 or dist[x] + 1 < dist[y]):
                    dist[y] = dist[x] + 1
    return dist
