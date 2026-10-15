#include <algolens.h>

std::vector<int> bfs_distances(int n, const std::vector<std::vector<int>>& edges, int source) {
    std::vector<std::vector<int>> adj(n);
    for (const auto& e : edges) {
        adj[e[0]].push_back(e[1]);
        adj[e[1]].push_back(e[0]);
    }
    std::vector<int> dist(n, -1);
    dist[source] = 0;
    std::deque<int> queue{source};
    while (!queue.empty()) {
        int u = queue.front();
        queue.pop_front();
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                queue.push_back(v);
            }
        }
    }
    return dist;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    int n = in["args"][0].get<int>();
    auto edges = in["args"][1].get<std::vector<std::vector<int>>>();
    algolens::emit(algolens::Json(bfs_distances(n, edges, in["args"][2].get<int>())).dump());
}
