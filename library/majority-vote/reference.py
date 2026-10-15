from collections import Counter


def reference(nums):
    return Counter(nums).most_common(1)[0][0]
