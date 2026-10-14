def reference(nums):
    # Try every set of houses with no two neighbours.
    def best(i):
        if i >= len(nums):
            return 0
        return max(best(i + 1), nums[i] + best(i + 2))

    return best(0)
