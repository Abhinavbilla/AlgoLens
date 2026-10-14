def reference(n, edges):
    # Repeatedly take the smallest node that no remaining edge points into.
    remaining = set(range(n))
    left = list(edges)
    order = []
    while remaining:
        targets = {v for u, v in left}
        u = min(x for x in remaining if x not in targets)
        order.append(u)
        remaining.remove(u)
        left = [(a, b) for a, b in left if a != u]
    return order
