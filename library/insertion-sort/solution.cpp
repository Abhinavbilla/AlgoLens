#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

std::vector<long long> insertion_sort(std::vector<long long> arr) {
    for (int i = 1; i < static_cast<int>(arr.size()); ++i) {
        long long key = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j -= 1;
        }
        arr[j + 1] = key;
    }
    return arr;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto result = insertion_sort(in["args"][0].get<std::vector<long long>>());
    algolens::emit(nlohmann::json(result).dump());
}
