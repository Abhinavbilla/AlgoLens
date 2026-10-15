def validate(nums):
    for v in set(nums):
        if nums.count(v) * 2 > len(nums):
            return None
    return "some value must appear more than half the time"
