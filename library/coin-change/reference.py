from functools import lru_cache


def reference(coins, amount):
    # Plain recursion over "which coin goes first", remembered so it finishes.
    @lru_cache(maxsize=None)
    def fewest(left):
        if left == 0:
            return 0
        options = [fewest(left - c) for c in coins if c <= left]
        options = [o for o in options if o >= 0]
        return 1 + min(options) if options else -1

    return fewest(amount)
