from itertools import combinations


def reference(nums):
    # No recursion: every combination of every size, from the standard library.
    every = [list(c) for k in range(len(nums) + 1) for c in combinations(nums, k)]
    return sorted(every)
