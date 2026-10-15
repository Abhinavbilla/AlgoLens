#include <algolens.h>

std::vector<long long> selection_sort(std::vector<long long> arr) {
    int n = static_cast<int>(arr.size());
    for (int i = 0; i < n - 1; ++i) {
        int smallest = i;
        for (int j = i + 1; j < n; ++j) {
            if (arr[j] < arr[smallest]) {
                smallest = j;
            }
        }
        std::swap(arr[i], arr[smallest]);
    }
    return arr;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(selection_sort(in["args"][0].get<std::vector<long long>>())).dump());
}
