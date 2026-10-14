def reference(nums, target):
    best = 0
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            if sum(nums[i : j + 1]) >= target:
                length = j - i + 1
                if best == 0 or length < best:
                    best = length
                break
    return best
