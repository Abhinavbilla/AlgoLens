#include <algolens.h>

int depth(algolens::TreeNode* node) {
    if (node == nullptr) {
        return 0;
    }
    int left = depth(node->left);
    int right = depth(node->right);
    return 1 + std::max(left, right);
}

int max_depth(algolens::TreeNode* root) {
    return depth(root);
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(max_depth(algolens::build_tree(in["args"][0]))).dump());
}
