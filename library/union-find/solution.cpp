#include <algolens.h>
#include <numeric>
#include <utility>
#include <vector>

int find_root(std::vector<int>& parent, int x) {
    while (parent[x] != x) {
        parent[x] = parent[parent[x]];
        x = parent[x];
    }
    return x;
}

int count_components(int n, const std::vector<std::vector<int>>& edges) {
    std::vector<int> parent(n);
    std::iota(parent.begin(), parent.end(), 0);
    std::vector<int> size(n, 1);
    int components = n;
    for (const auto& e : edges) {
        int ru = find_root(parent, e[0]), rv = find_root(parent, e[1]);
        if (ru == rv) {
            continue;
        }
        if (size[ru] < size[rv]) {
            std::swap(ru, rv);
        }
        parent[rv] = ru;
        size[ru] += size[rv];
        components -= 1;
    }
    return components;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    int n = in["args"][0].get<int>();
    auto edges = in["args"][1].get<std::vector<std::vector<int>>>();
    algolens::emit(algolens::Json(count_components(n, edges)).dump());
}
