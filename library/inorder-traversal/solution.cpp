#include <algolens.h>
#include <deque>
#include <vector>

struct TreeNode {
    int val;
    TreeNode* left = nullptr;
    TreeNode* right = nullptr;
    explicit TreeNode(int v) : val(v) {}
};

void visit(TreeNode* node, std::vector<int>& order) {
    if (node == nullptr) {
        return;
    }
    visit(node->left, order);
    order.push_back(node->val);
    visit(node->right, order);
}

std::vector<int> inorder(TreeNode* root) {
    std::vector<int> order;
    visit(root, order);
    return order;
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
    algolens::emit(algolens::Json(inorder(build(in["args"][0]))).dump());
}
