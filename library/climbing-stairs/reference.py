from functools import lru_cache


def reference(n):
    @lru_cache(maxsize=None)
    def ways(k):
        return 1 if k <= 1 else ways(k - 1) + ways(k - 2)

    return ways(n)
