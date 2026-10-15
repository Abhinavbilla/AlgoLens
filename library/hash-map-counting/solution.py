def two_sum(nums, target):
    seen = {}
    for j in range(len(nums)):
        need = target - nums[j]
        if need in seen:
            return [seen[need], j]
        seen[nums[j]] = j
    return []
