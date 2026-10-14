from itertools import combinations


def reference(a, b):
    # Brute force: try every subsequence of a, longest first, and check it against b.
    def is_subsequence(s, t):
        it = iter(t)
        return all(ch in it for ch in s)

    for k in range(len(a), 0, -1):
        for picked in combinations(a, k):
            if is_subsequence(picked, b):
                return k
    return 0
