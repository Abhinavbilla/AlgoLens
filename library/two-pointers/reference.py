def reference(nums, target):
    # Every pair, simplest first. The test inputs have at most one valid pair.
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
