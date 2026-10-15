#include <algolens.h>

long long majority(const std::vector<long long>& nums) {
    long long candidate = 0;
    int count = 0;
    for (long long x : nums) {
        if (count == 0) {
            candidate = x;
        }
        count += x == candidate ? 1 : -1;
    }
    return candidate;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(majority(in["args"][0].get<std::vector<long long>>())).dump());
}
