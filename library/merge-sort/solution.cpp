#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

std::vector<long long> merge_sort(std::vector<long long> arr) {
    if (arr.size() <= 1) {
        return arr;
    }
    size_t mid = arr.size() / 2;
    std::vector<long long> left = merge_sort(std::vector<long long>(arr.begin(), arr.begin() + mid));
    std::vector<long long> right = merge_sort(std::vector<long long>(arr.begin() + mid, arr.end()));
    std::vector<long long> merged;
    size_t i = 0, j = 0;
    while (i < left.size() && j < right.size()) {
        if (left[i] <= right[j]) {
            merged.push_back(left[i]);
            i += 1;
        } else {
            merged.push_back(right[j]);
            j += 1;
        }
    }
    merged.insert(merged.end(), left.begin() + i, left.end());
    merged.insert(merged.end(), right.begin() + j, right.end());
    return merged;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto result = merge_sort(in["args"][0].get<std::vector<long long>>());
    algolens::emit(nlohmann::json(result).dump());
}
