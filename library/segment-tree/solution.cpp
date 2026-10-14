#include <algolens.h>
#include <nlohmann/json.hpp>
#include <vector>

struct SegmentTree {
    const std::vector<long long>& nums;
    std::vector<long long> tree;

    explicit SegmentTree(const std::vector<long long>& values)
        : nums(values), tree(4 * values.size(), 0) {}

    void build(int node, int lo, int hi) {
        if (lo == hi) {
            tree[node] = nums[lo];
            return;
        }
        int mid = (lo + hi) / 2;
        build(2 * node, lo, mid);
        build(2 * node + 1, mid + 1, hi);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }

    long long query(int node, int lo, int hi, int l, int r) const {
        if (r < lo || hi < l) {
            return 0;
        }
        if (l <= lo && hi <= r) {
            return tree[node];
        }
        int mid = (lo + hi) / 2;
        return query(2 * node, lo, mid, l, r) + query(2 * node + 1, mid + 1, hi, l, r);
    }
};

std::vector<long long> range_sum_queries(const std::vector<long long>& nums,
                                         const std::vector<std::vector<int>>& queries) {
    int n = static_cast<int>(nums.size());
    SegmentTree st(nums);
    st.build(1, 0, n - 1);
    std::vector<long long> answers;
    for (const auto& q : queries) {
        answers.push_back(st.query(1, 0, n - 1, q[0], q[1]));
    }
    return answers;
}

int main() {
    auto in = nlohmann::json::parse(algolens::read_input());
    auto nums = in["args"][0].get<std::vector<long long>>();
    auto queries = in["args"][1].get<std::vector<std::vector<int>>>();
    algolens::emit(nlohmann::json(range_sum_queries(nums, queries)).dump());
}
