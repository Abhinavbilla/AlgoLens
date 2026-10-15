from itertools import combinations


def reference(nums):
    # Try every subsequence, longest first.
    for size in range(len(nums), 0, -1):
        for pick in combinations(nums, size):
            if all(pick[i] < pick[i + 1] for i in range(size - 1)):
                return size
    return 0
