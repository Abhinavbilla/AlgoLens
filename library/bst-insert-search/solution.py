def bst_contains(values, target):
    root = None
    for v in values:
        root = insert(root, v)
    node = root
    while node is not None and node.val != target:
        node = node.left if target < node.val else node.right
    return node is not None


def insert(node, v):
    if node is None:
        return TreeNode(v)
    if v < node.val:
        node.left = insert(node.left, v)
    else:
        node.right = insert(node.right, v)
    return node
