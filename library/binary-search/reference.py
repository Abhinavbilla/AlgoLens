import bisect


def reference(nums, target):
    return bisect.bisect_left(nums, target)
