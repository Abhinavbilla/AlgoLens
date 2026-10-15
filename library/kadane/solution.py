def max_subarray(nums):
    best = nums[0]
    current = 0
    for x in nums:
        current = max(x, current + x)
        best = max(best, current)
    return best
