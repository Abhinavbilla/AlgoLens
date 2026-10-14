def reference(weights, values, capacity):
    # Try every subset of items.
    best = 0
    n = len(weights)
    for mask in range(1 << n):
        w = sum(weights[i] for i in range(n) if mask >> i & 1)
        if w <= capacity:
            best = max(best, sum(values[i] for i in range(n) if mask >> i & 1))
    return best
