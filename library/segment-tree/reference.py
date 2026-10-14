def reference(nums, queries):
    return [sum(nums[l : r + 1]) for l, r in queries]
