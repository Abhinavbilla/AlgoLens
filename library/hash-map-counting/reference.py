def reference(nums, target):
    # Every pair, by the later index first; for that index, the latest earlier partner.
    for j in range(len(nums)):
        for i in range(j - 1, -1, -1):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
