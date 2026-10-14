#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

long long knapsack(const std::vector<long long>& weights, const std::vector<long long>& values,
                   int capacity) {
    int n = static_cast<int>(weights.size());
    std::vector<std::vector<long long>> dp(n + 1, std::vector<long long>(capacity + 1, 0));
    for (int i = 1; i <= n; ++i) {
        long long w = weights[i - 1], v = values[i - 1];
        for (int c = 0; c <= capacity; ++c) {
            dp[i][c] = dp[i - 1][c];
            if (w <= c && dp[i - 1][c - w] + v > dp[i][c]) {
                dp[i][c] = dp[i - 1][c - w] + v;
            }
        }
    }
    return dp[n][capacity];
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto weights = in["args"][0].get<std::vector<long long>>();
    auto values = in["args"][1].get<std::vector<long long>>();
    auto capacity = in["args"][2].get<int>();
    algolens::emit(nlohmann::json(knapsack(weights, values, capacity)).dump());
}
