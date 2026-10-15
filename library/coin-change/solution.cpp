#include <algolens.h>
#include <vector>

long long coin_change(const std::vector<long long>& coins, int amount) {
    long long INF = amount + 1;
    std::vector<long long> dp(amount + 1, INF);
    dp[0] = 0;
    for (int a = 1; a <= amount; ++a) {
        for (long long c : coins) {
            if (c <= a && dp[a - c] + 1 < dp[a]) {
                dp[a] = dp[a - c] + 1;
            }
        }
    }
    return dp[amount] != INF ? dp[amount] : -1;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto coins = in["args"][0].get<std::vector<long long>>();
    auto amount = in["args"][1].get<int>();
    algolens::emit(algolens::Json(coin_change(coins, amount)).dump());
}
