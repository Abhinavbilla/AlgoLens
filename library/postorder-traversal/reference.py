def reference(root):
    # Node, right, left with a stack, reversed, is left, right, node.
    out, stack = [], [root]
    while stack:
        node = stack.pop()
        if node is not None:
            out.append(node.val)
            stack.append(node.left)
            stack.append(node.right)
    return out[::-1]
