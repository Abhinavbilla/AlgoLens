def reference(s):
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s) + 1):
            if len(set(s[i:j])) == j - i:
                best = max(best, j - i)
    return best
