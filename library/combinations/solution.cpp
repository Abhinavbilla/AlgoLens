#include <algolens.h>

void backtrack(int start, int n, int k, std::vector<int>& path, std::vector<std::vector<int>>& result) {
    if (static_cast<int>(path.size()) == k) {
        result.push_back(path);
        return;
    }
    for (int x = start; x <= n; ++x) {
        path.push_back(x);
        backtrack(x + 1, n, k, path, result);
        path.pop_back();
    }
}

std::vector<std::vector<int>> combine(int n, int k) {
    std::vector<std::vector<int>> result;
    std::vector<int> path;
    backtrack(1, n, k, path, result);
    return result;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(combine(in["args"][0].get<int>(), in["args"][1].get<int>())).dump());
}
