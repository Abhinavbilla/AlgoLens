def lis(nums):
    best = [1] * len(nums)
    for i in range(len(nums)):
        for j in range(i):
            if nums[j] < nums[i] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
    return max(best) if best else 0
