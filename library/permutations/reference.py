from itertools import permutations as all_orders


def reference(nums):
    return [list(p) for p in all_orders(nums)]
