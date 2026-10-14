def range_sum_queries(nums, queries):
    n = len(nums)
    tree = [0] * (4 * n)

    def build(node, lo, hi):
        if lo == hi:
            tree[node] = nums[lo]
            return
        mid = (lo + hi) // 2
        build(2 * node, lo, mid)
        build(2 * node + 1, mid + 1, hi)
        tree[node] = tree[2 * node] + tree[2 * node + 1]

    def query(node, lo, hi, l, r):
        if r < lo or hi < l:
            return 0
        if l <= lo and hi <= r:
            return tree[node]
        mid = (lo + hi) // 2
        return query(2 * node, lo, mid, l, r) + query(2 * node + 1, mid + 1, hi, l, r)

    build(1, 0, n - 1)
    return [query(1, 0, n - 1, l, r) for l, r in queries]
