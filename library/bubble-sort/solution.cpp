#include <algolens.h>
#include <nlohmann/json.hpp>
#include <utility>
#include <vector>

std::vector<long long> bubble_sort(std::vector<long long> arr) {
    int n = static_cast<int>(arr.size());
    for (int i = 0; i < n - 1; ++i) {
        bool swapped = false;
        for (int j = 0; j < n - 1 - i; ++j) {
            if (arr[j] > arr[j + 1]) {
                std::swap(arr[j], arr[j + 1]);
                swapped = true;
            }
        }
        if (!swapped) {
            break;
        }
    }
    return arr;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto result = bubble_sort(in["args"][0].get<std::vector<long long>>());
    algolens::emit(nlohmann::json(result).dump());
}
