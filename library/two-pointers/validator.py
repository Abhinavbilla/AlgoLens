def validate(nums, target):
    # The schema already guarantees a sorted list of ints. The extra rule: at most one pair
    # adds up to the target, so there's exactly one right answer to compare against.
    pairs = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                pairs += 1
                if pairs > 1:
                    return f"more than one pair adds up to {target}; this problem needs at most one"
    return None
