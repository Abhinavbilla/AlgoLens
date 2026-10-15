#include <algolens.h>

int binary_search(const std::vector<long long>& nums, long long target) {
    int lo = 0, hi = static_cast<int>(nums.size()) - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (nums[mid] == target) {
            return mid;
        }
        if (nums[mid] < target) {
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return -1;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    algolens::emit(algolens::Json(binary_search(nums, in["args"][1].get<long long>())).dump());
}
