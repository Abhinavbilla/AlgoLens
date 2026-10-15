// Helpers for C++ test programs run by the AlgoLens sandbox driver.
// The test input arrives as JSON on stdin; the result must be written as JSON with emit(),
// which uses fd 3 so the program's own std::cout output never corrupts the result.
//
// This header is precompiled in the sandbox image (algolens.h.gch, built with the same
// flags the sandbox compiles with), so make it the first #include of a solution: parsing
// nlohmann/json takes ~2.5 s otherwise, which a busy machine can stretch past the limit.
#pragma once

#include <unistd.h>

// The standard headers solutions commonly use come with it too, at no compile-time cost
// (they're in the precompiled header), so a forgotten #include isn't a failure.
#include <algorithm>
#include <array>
#include <bitset>
#include <climits>
#include <cmath>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <iterator>
#include <limits>
#include <list>
#include <map>
#include <nlohmann/json.hpp>
#include <numeric>
#include <queue>
#include <set>
#include <sstream>
#include <stack>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace algolens {

using Json = nlohmann::json;

inline std::string read_input() {
    return std::string(std::istreambuf_iterator<char>(std::cin), std::istreambuf_iterator<char>());
}

inline void emit(const std::string& json) {
    const char* p = json.data();
    size_t left = json.size();
    while (left > 0) {
        ssize_t n = ::write(3, p, left);
        if (n <= 0) return;
        p += n;
        left -= static_cast<size_t>(n);
    }
}

// Binary trees and linked lists, as the inputs describe them: a tree is a level-order list with
// null for a missing child, a linked list is a plain list.
struct TreeNode {
    long long val;
    TreeNode* left = nullptr;
    TreeNode* right = nullptr;
    explicit TreeNode(long long v) : val(v) {}
};

struct ListNode {
    long long val;
    ListNode* next = nullptr;
    explicit ListNode(long long v) : val(v) {}
};

inline TreeNode* build_tree(const Json& items) {
    if (!items.is_array() || items.empty() || items[0].is_null()) return nullptr;
    auto* root = new TreeNode(items[0].get<long long>());
    std::deque<TreeNode*> queue{root};
    size_t i = 1;
    while (!queue.empty() && i < items.size()) {
        TreeNode* node = queue.front();
        queue.pop_front();
        for (TreeNode** child : {&node->left, &node->right}) {
            if (i < items.size() && !items[i].is_null()) {
                *child = new TreeNode(items[i].get<long long>());
                queue.push_back(*child);
            }
            ++i;
        }
    }
    return root;
}

// Level order with null for gaps, trailing nulls dropped (the format the checker expects).
inline Json to_json(TreeNode* root) {
    Json out = Json::array();
    std::deque<TreeNode*> queue{root};
    while (!queue.empty()) {
        TreeNode* node = queue.front();
        queue.pop_front();
        if (node == nullptr) {
            out.push_back(nullptr);
            continue;
        }
        out.push_back(node->val);
        queue.push_back(node->left);
        queue.push_back(node->right);
    }
    while (!out.empty() && out.back().is_null()) out.erase(out.end() - 1);
    return out;
}

inline ListNode* build_list(const Json& items) {
    ListNode head(0);
    ListNode* tail = &head;
    for (const auto& v : items) {
        tail->next = new ListNode(v.get<long long>());
        tail = tail->next;
    }
    return head.next;
}

inline Json to_json(ListNode* head) {
    Json out = Json::array();
    for (; head != nullptr; head = head->next) out.push_back(head->val);
    return out;
}

}  // namespace algolens
