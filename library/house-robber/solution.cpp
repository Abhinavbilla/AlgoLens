#include <algolens.h>
#include <algorithm>
#include <nlohmann/json.hpp>
#include <vector>

long long rob(const std::vector<long long>& nums) {
    int n = static_cast<int>(nums.size());
    std::vector<long long> dp(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        long long skip = dp[i - 1];
        long long take = i >= 2 ? dp[i - 2] + nums[i - 1] : nums[i - 1];
        dp[i] = std::max(skip, take);
    }
    return dp[n];
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    algolens::emit(nlohmann::json(rob(in["args"][0].get<std::vector<long long>>())).dump());
}
