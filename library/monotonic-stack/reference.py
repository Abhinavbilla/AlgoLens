def reference(nums):
    # For each position, scan everything to its right: O(n^2), but obviously correct.
    out = []
    for i in range(len(nums)):
        greater = -1
        for y in nums[i + 1 :]:
            if y > nums[i]:
                greater = y
                break
        out.append(greater)
    return out
