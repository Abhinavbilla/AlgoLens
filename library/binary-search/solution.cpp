#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

int lower_bound(const std::vector<long long>& nums, long long target) {
    int lo = 0, hi = static_cast<int>(nums.size());
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (nums[mid] < target) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return lo;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto target = in["args"][1].get<long long>();
    algolens::emit(nlohmann::json(lower_bound(nums, target)).dump());
}
