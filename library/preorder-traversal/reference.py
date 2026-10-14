def reference(root):
    # Iterative, with an explicit stack: right is pushed first so left comes out first.
    out, stack = [], [root]
    while stack:
        node = stack.pop()
        if node is not None:
            out.append(node.val)
            stack.append(node.right)
            stack.append(node.left)
    return out
