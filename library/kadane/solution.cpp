#include <algolens.h>

long long max_subarray(const std::vector<long long>& nums) {
    long long best = nums[0];
    long long current = 0;
    for (long long x : nums) {
        current = std::max(x, current + x);
        best = std::max(best, current);
    }
    return best;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(max_subarray(in["args"][0].get<std::vector<long long>>())).dump());
}
