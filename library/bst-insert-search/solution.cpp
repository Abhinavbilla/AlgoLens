#include <algolens.h>
#include <vector>

algolens::TreeNode* insert(algolens::TreeNode* node, long long v) {
    if (node == nullptr) {
        return new algolens::TreeNode(v);
    }
    if (v < node->val) {
        node->left = insert(node->left, v);
    } else {
        node->right = insert(node->right, v);
    }
    return node;
}

bool bst_contains(const std::vector<long long>& values, long long target) {
    algolens::TreeNode* root = nullptr;
    for (long long v : values) {
        root = insert(root, v);
    }
    algolens::TreeNode* node = root;
    while (node != nullptr && node->val != target) {
        node = target < node->val ? node->left : node->right;
    }
    return node != nullptr;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto values = in["args"][0].get<std::vector<long long>>();
    auto target = in["args"][1].get<long long>();
    algolens::emit(algolens::Json(bst_contains(values, target)).dump());
}
