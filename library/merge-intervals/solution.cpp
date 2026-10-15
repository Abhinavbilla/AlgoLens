#include <algolens.h>
#include <algorithm>
#include <vector>

std::vector<std::vector<long long>> merge_intervals(std::vector<std::vector<long long>> intervals) {
    std::sort(intervals.begin(), intervals.end());
    std::vector<std::vector<long long>> merged;
    for (const auto& iv : intervals) {
        long long start = iv[0], end = iv[1];
        if (!merged.empty() && start <= merged.back()[1]) {
            merged.back()[1] = std::max(merged.back()[1], end);
        } else {
            merged.push_back({start, end});
        }
    }
    return merged;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto intervals = in["args"][0].get<std::vector<std::vector<long long>>>();
    algolens::emit(algolens::Json(merge_intervals(intervals)).dump());
}
