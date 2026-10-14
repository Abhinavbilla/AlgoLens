#include <algolens.h>
#include <algorithm>
#include <string>
#include <vector>

int lcs(const std::string& a, const std::string& b) {
    int m = a.size(), n = b.size();
    std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1, 0));
    for (int i = 1; i <= m; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (a[i - 1] == b[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = std::max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }
    return dp[m][n];
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto a = in["args"][0].get<std::string>();
    auto b = in["args"][1].get<std::string>();
    algolens::emit(algolens::Json(lcs(a, b)).dump());
}
