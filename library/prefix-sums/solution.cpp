#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

std::vector<long long> range_sums(const std::vector<long long>& nums,
                                  const std::vector<std::vector<int>>& queries) {
    std::vector<long long> prefix{0};
    for (long long x : nums) {
        prefix.push_back(prefix.back() + x);
    }
    std::vector<long long> answers;
    for (const auto& q : queries) {
        int l = q[0], r = q[1];
        answers.push_back(prefix[r + 1] - prefix[l]);
    }
    return answers;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto queries = in["args"][1].get<std::vector<std::vector<int>>>();
    algolens::emit(nlohmann::json(range_sums(nums, queries)).dump());
}
