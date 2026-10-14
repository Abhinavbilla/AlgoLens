def reference(grid):
    # Not BFS: keep relaxing every open cell's distance until nothing changes.
    rows, cols = len(grid), len(grid[0])
    if grid[0][0] == "#":
        return -1
    dist = {(0, 0): 0}
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            for c in range(cols):
                if (r, c) not in dist:
                    continue
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == ".":
                        if (nr, nc) not in dist or dist[(nr, nc)] > dist[(r, c)] + 1:
                            dist[(nr, nc)] = dist[(r, c)] + 1
                            changed = True
    return dist.get((rows - 1, cols - 1), -1)
