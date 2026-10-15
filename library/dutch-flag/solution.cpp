#include <algolens.h>

std::vector<long long> sort_colors(std::vector<long long> nums) {
    int low = 0, mid = 0, high = static_cast<int>(nums.size()) - 1;
    while (mid <= high) {
        if (nums[mid] == 0) {
            std::swap(nums[low], nums[mid]);
            low += 1;
            mid += 1;
        } else if (nums[mid] == 1) {
            mid += 1;
        } else {
            std::swap(nums[mid], nums[high]);
            high -= 1;
        }
    }
    return nums;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(sort_colors(in["args"][0].get<std::vector<long long>>())).dump());
}
