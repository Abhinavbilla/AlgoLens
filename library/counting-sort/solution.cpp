#include <algolens.h>

std::vector<long long> counting_sort(const std::vector<long long>& arr) {
    if (arr.empty()) {
        return arr;
    }
    long long low = *std::min_element(arr.begin(), arr.end());
    long long high = *std::max_element(arr.begin(), arr.end());
    std::vector<int> counts(high - low + 1, 0);
    for (long long x : arr) {
        counts[x - low] += 1;
    }
    std::vector<long long> out;
    for (long long v = low; v <= high; ++v) {
        out.insert(out.end(), counts[v - low], v);
    }
    return out;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(counting_sort(in["args"][0].get<std::vector<long long>>())).dump());
}
