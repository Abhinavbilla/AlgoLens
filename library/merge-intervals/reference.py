def reference(intervals):
    # Keep merging any two overlapping intervals until none overlap, then sort.
    parts = [list(i) for i in intervals]
    changed = True
    while changed:
        changed = False
        for a in range(len(parts)):
            for b in range(a + 1, len(parts)):
                (s1, e1), (s2, e2) = parts[a], parts[b]
                if s1 <= e2 and s2 <= e1:
                    parts[a] = [min(s1, s2), max(e1, e2)]
                    del parts[b]
                    changed = True
                    break
            if changed:
                break
    return sorted(parts)
