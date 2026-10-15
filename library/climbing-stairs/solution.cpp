#include <algolens.h>

long long climb_stairs(int n) {
    std::vector<long long> ways(n + 1, 1);
    for (int i = 2; i <= n; ++i) {
        ways[i] = ways[i - 1] + ways[i - 2];
    }
    return ways[n];
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(climb_stairs(in["args"][0].get<int>())).dump());
}
