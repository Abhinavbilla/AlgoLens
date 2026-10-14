#include <algolens.h>
#include <deque>
#include <vector>

struct TreeNode {
    int val;
    TreeNode* left = nullptr;
    TreeNode* right = nullptr;
    explicit TreeNode(int v) : val(v) {}
};

std::vector<std::vector<int>> level_order(TreeNode* root) {
    std::vector<std::vector<int>> levels;
    std::deque<TreeNode*> queue;
    if (root) queue.push_back(root);
    while (!queue.empty()) {
        std::vector<int> level;
        for (size_t k = queue.size(); k > 0; --k) {
            TreeNode* node = queue.front();
            queue.pop_front();
            level.push_back(node->val);
            if (node->left) queue.push_back(node->left);
            if (node->right) queue.push_back(node->right);
        }
        levels.push_back(level);
    }
    return levels;
}

// The tree arrives in level order, with null for missing children.
TreeNode* build(const algolens::Json& items) {
    if (items.empty()) return nullptr;
    auto* root = new TreeNode(items[0].get<int>());
    std::deque<TreeNode*> queue{root};
    size_t i = 1;
    while (!queue.empty() && i < items.size()) {
        TreeNode* node = queue.front();
        queue.pop_front();
        for (TreeNode** child : {&node->left, &node->right}) {
            if (i < items.size() && !items[i].is_null()) {
                *child = new TreeNode(items[i].get<int>());
                queue.push_back(*child);
            }
            ++i;
        }
    }
    return root;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(level_order(build(in["args"][0]))).dump());
}
