#include <algolens.h>
#include <deque>
#include <string>
#include <utility>
#include <vector>

using Grid = std::vector<std::vector<std::string>>;

int shortest_path(const Grid& grid) {
    int rows = grid.size(), cols = grid[0].size();
    if (grid[0][0] == "#" || grid[rows - 1][cols - 1] == "#") {
        return -1;
    }
    std::vector<std::vector<int>> dist(rows, std::vector<int>(cols, -1));
    dist[0][0] = 0;
    std::deque<std::pair<int, int>> queue{{0, 0}};
    while (!queue.empty()) {
        auto [r, c] = queue.front();
        queue.pop_front();
        if (r == rows - 1 && c == cols - 1) {
            return dist[r][c];
        }
        const int dirs[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (const auto& d : dirs) {
            int nr = r + d[0], nc = c + d[1];
            if (0 <= nr && nr < rows && 0 <= nc && nc < cols && grid[nr][nc] == "." && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                queue.push_back({nr, nc});
            }
        }
    }
    return -1;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(shortest_path(in["args"][0].get<Grid>())).dump());
}
