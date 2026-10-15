def combine(n, k):
    result = []
    path = []

    def backtrack(start):
        if len(path) == k:
            result.append(path[:])
            return
        for x in range(start, n + 1):
            path.append(x)
            backtrack(x + 1)
            path.pop()

    backtrack(1)
    return result
