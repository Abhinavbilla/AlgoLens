#include <algolens.h>

std::vector<long long> k_largest(const std::vector<long long>& nums, int k) {
    std::priority_queue<long long, std::vector<long long>, std::greater<long long>> heap;
    for (long long x : nums) {
        heap.push(x);
        if (static_cast<int>(heap.size()) > k) {
            heap.pop();
        }
    }
    std::vector<long long> out;
    while (!heap.empty()) {
        out.push_back(heap.top());
        heap.pop();
    }
    std::reverse(out.begin(), out.end());
    return out;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    algolens::emit(algolens::Json(k_largest(nums, in["args"][1].get<int>())).dump());
}
