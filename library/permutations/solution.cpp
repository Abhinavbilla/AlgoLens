#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

void backtrack(const std::vector<long long>& nums, std::vector<long long>& path,
               std::vector<bool>& used, std::vector<std::vector<long long>>& result) {
    if (path.size() == nums.size()) {
        result.push_back(path);
        return;
    }
    for (size_t i = 0; i < nums.size(); ++i) {
        if (used[i]) {
            continue;
        }
        used[i] = true;
        path.push_back(nums[i]);
        backtrack(nums, path, used, result);
        path.pop_back();
        used[i] = false;
    }
}

std::vector<std::vector<long long>> permutations(const std::vector<long long>& nums) {
    std::vector<std::vector<long long>> result;
    std::vector<long long> path;
    std::vector<bool> used(nums.size(), false);
    backtrack(nums, path, used, result);
    return result;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto result = permutations(in["args"][0].get<std::vector<long long>>());
    algolens::emit(nlohmann::json(result).dump());
}
