#include <algolens.h>
#include <unordered_map>
#include <vector>

std::vector<int> two_sum(const std::vector<long long>& nums, long long target) {
    std::unordered_map<long long, int> seen;
    for (int j = 0; j < static_cast<int>(nums.size()); ++j) {
        long long need = target - nums[j];
        if (seen.count(need)) {
            return {seen[need], j};
        }
        seen[nums[j]] = j;
    }
    return {};
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto target = in["args"][1].get<long long>();
    algolens::emit(algolens::Json(two_sum(nums, target)).dump());
}
