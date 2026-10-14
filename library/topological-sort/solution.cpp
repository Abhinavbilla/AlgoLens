#include <algolens.h>
#include <functional>
#include <queue>
#include <vector>

std::vector<int> topo_sort(int n, const std::vector<std::vector<int>>& edges) {
    std::vector<int> indegree(n, 0);
    std::vector<std::vector<int>> adj(n);
    for (const auto& e : edges) {
        adj[e[0]].push_back(e[1]);
        indegree[e[1]] += 1;
    }
    std::priority_queue<int, std::vector<int>, std::greater<int>> ready;
    for (int u = 0; u < n; ++u) {
        if (indegree[u] == 0) ready.push(u);
    }
    std::vector<int> order;
    while (!ready.empty()) {
        int u = ready.top();
        ready.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            indegree[v] -= 1;
            if (indegree[v] == 0) {
                ready.push(v);
            }
        }
    }
    return order;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    int n = in["args"][0].get<int>();
    auto edges = in["args"][1].get<std::vector<std::vector<int>>>();
    algolens::emit(algolens::Json(topo_sort(n, edges)).dump());
}
