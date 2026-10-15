#include <algolens.h>

bool can_jump(const std::vector<long long>& nums) {
    long long reach = 0;
    for (long long i = 0; i < static_cast<long long>(nums.size()); ++i) {
        if (i > reach) {
            return false;
        }
        reach = std::max(reach, i + nums[i]);
    }
    return true;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(can_jump(in["args"][0].get<std::vector<long long>>())).dump());
}
