#include <algolens.h>
#include <vector>

void visit(int u, const std::vector<std::vector<int>>& adj, std::vector<bool>& visited,
           std::vector<int>& order) {
    visited[u] = true;
    order.push_back(u);
    for (int v : adj[u]) {
        if (!visited[v]) {
            visit(v, adj, visited, order);
        }
    }
}

std::vector<int> dfs_order(int n, const std::vector<std::vector<int>>& edges, int source) {
    std::vector<std::vector<int>> adj(n);
    for (const auto& e : edges) {
        adj[e[0]].push_back(e[1]);
        adj[e[1]].push_back(e[0]);
    }
    std::vector<bool> visited(n, false);
    std::vector<int> order;
    visit(source, adj, visited, order);
    return order;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    int n = in["args"][0].get<int>();
    auto edges = in["args"][1].get<std::vector<std::vector<int>>>();
    int source = in["args"][2].get<int>();
    algolens::emit(algolens::Json(dfs_order(n, edges, source)).dump());
}
