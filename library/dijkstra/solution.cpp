#include <algolens.h>
#include <functional>
#include <queue>
#include <utility>
#include <vector>

std::vector<long long> dijkstra(int n, const std::vector<std::vector<long long>>& edges, int source) {
    std::vector<std::vector<std::pair<int, long long>>> adj(n);
    for (const auto& e : edges) {
        adj[e[0]].push_back({static_cast<int>(e[1]), e[2]});
        adj[e[1]].push_back({static_cast<int>(e[0]), e[2]});
    }
    std::vector<long long> dist(n, -1);
    dist[source] = 0;
    using Item = std::pair<long long, int>;
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> heap;
    heap.push({0, source});
    while (!heap.empty()) {
        auto [d, u] = heap.top();
        heap.pop();
        if (d > dist[u]) {
            continue;
        }
        for (auto [v, w] : adj[u]) {
            if (dist[v] == -1 || d + w < dist[v]) {
                dist[v] = d + w;
                heap.push({dist[v], v});
            }
        }
    }
    return dist;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    int n = in["args"][0].get<int>();
    auto edges = in["args"][1].get<std::vector<std::vector<long long>>>();
    int source = in["args"][2].get<int>();
    algolens::emit(algolens::Json(dijkstra(n, edges, source)).dump());
}
