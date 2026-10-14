#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

std::vector<int> two_sum_sorted(const std::vector<long long>& nums, long long target) {
    int l = 0, r = static_cast<int>(nums.size()) - 1;
    while (l < r) {
        long long s = nums[l] + nums[r];
        if (s == target) {
            return {l, r};
        }
        if (s < target) {
            ++l;
        } else {
            --r;
        }
    }
    return {};
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto target = in["args"][1].get<long long>();
    algolens::emit(nlohmann::json(two_sum_sorted(nums, target)).dump());
}
