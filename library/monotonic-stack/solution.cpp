#include <algolens.h>
#include <vector>

std::vector<long long> next_greater(const std::vector<long long>& nums) {
    std::vector<long long> answer(nums.size(), -1);
    std::vector<int> stack;
    for (int i = 0; i < static_cast<int>(nums.size()); ++i) {
        long long x = nums[i];
        while (!stack.empty() && nums[stack.back()] < x) {
            int j = stack.back();
            stack.pop_back();
            answer[j] = x;
        }
        stack.push_back(i);
    }
    return answer;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    algolens::emit(algolens::Json(next_greater(nums)).dump());
}
