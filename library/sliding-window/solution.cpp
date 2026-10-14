#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

long long min_window_len(const std::vector<long long>& nums, long long target) {
    long long best = 0;
    long long total = 0;
    int left = 0;
    for (int right = 0; right < static_cast<int>(nums.size()); ++right) {
        total += nums[right];
        while (total >= target) {
            if (best == 0 || right - left + 1 < best) {
                best = right - left + 1;
            }
            total -= nums[left];
            left += 1;
        }
    }
    return best;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto target = in["args"][1].get<long long>();
    algolens::emit(nlohmann::json(min_window_len(nums, target)).dump());
}
