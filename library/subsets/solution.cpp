#include <algolens.h>
#include <algorithm>
#include <vector>

using Subsets = std::vector<std::vector<int>>;

void backtrack(const std::vector<int>& nums, int start, std::vector<int>& path, Subsets& result) {
    result.push_back(path);
    for (int i = start; i < static_cast<int>(nums.size()); ++i) {
        path.push_back(nums[i]);
        backtrack(nums, i + 1, path, result);
        path.pop_back();
    }
}

Subsets subsets(const std::vector<int>& nums) {
    Subsets result;
    std::vector<int> path;
    backtrack(nums, 0, path, result);
    std::sort(result.begin(), result.end());
    return result;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(subsets(in["args"][0].get<std::vector<int>>())).dump());
}
