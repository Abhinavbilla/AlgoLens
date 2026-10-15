def counting_sort(arr):
    if not arr:
        return arr
    low, high = min(arr), max(arr)
    counts = [0] * (high - low + 1)
    for x in arr:
        counts[x - low] += 1
    out = []
    for v in range(low, high + 1):
        out.extend([v] * counts[v - low])
    return out
