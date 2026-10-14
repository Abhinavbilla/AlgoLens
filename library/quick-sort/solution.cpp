#include <algolens.h>
#include <nlohmann/json.hpp>
#include <utility>
#include <vector>

void sort_part(std::vector<long long>& arr, int lo, int hi) {
    if (lo >= hi) {
        return;
    }
    long long pivot = arr[hi];
    int p = lo;
    for (int k = lo; k < hi; ++k) {
        if (arr[k] < pivot) {
            std::swap(arr[p], arr[k]);
            p += 1;
        }
    }
    std::swap(arr[p], arr[hi]);
    sort_part(arr, lo, p - 1);
    sort_part(arr, p + 1, hi);
}

std::vector<long long> quick_sort(std::vector<long long> arr) {
    sort_part(arr, 0, static_cast<int>(arr.size()) - 1);
    return arr;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto result = quick_sort(in["args"][0].get<std::vector<long long>>());
    algolens::emit(nlohmann::json(result).dump());
}
