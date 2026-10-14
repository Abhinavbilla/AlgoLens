from collections import deque


def shortest_path(grid):
    rows, cols = len(grid), len(grid[0])
    if grid[0][0] == "#" or grid[rows - 1][cols - 1] == "#":
        return -1
    dist = [[-1] * cols for _ in range(rows)]
    dist[0][0] = 0
    queue = deque([(0, 0)])
    while queue:
        r, c = queue.popleft()
        if r == rows - 1 and c == cols - 1:
            return dist[r][c]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "." and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return -1
