def max_depth(root):
    return depth(root)


def depth(node):
    if node is None:
        return 0
    left = depth(node.left)
    right = depth(node.right)
    return 1 + max(left, right)
