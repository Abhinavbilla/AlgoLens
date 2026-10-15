from itertools import combinations


def reference(n, k):
    return [list(c) for c in combinations(range(1, n + 1), k)]
