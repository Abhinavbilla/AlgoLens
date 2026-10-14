def min_window_len(nums, target):
    best = 0
    total = 0
    left = 0
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            if best == 0 or right - left + 1 < best:
                best = right - left + 1
            total -= nums[left]
            left += 1
    return best
