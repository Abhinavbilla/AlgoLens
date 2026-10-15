#include <algolens.h>

int lis(const std::vector<long long>& nums) {
    std::vector<int> best(nums.size(), 1);
    for (size_t i = 0; i < nums.size(); ++i) {
        for (size_t j = 0; j < i; ++j) {
            if (nums[j] < nums[i] && best[j] + 1 > best[i]) {
                best[i] = best[j] + 1;
            }
        }
    }
    return best.empty() ? 0 : *std::max_element(best.begin(), best.end());
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(lis(in["args"][0].get<std::vector<long long>>())).dump());
}
