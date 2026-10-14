def inorder(root):
    order = []

    def visit(node):
        if node is None:
            return
        visit(node.left)
        order.append(node.val)
        visit(node.right)

    visit(root)
    return order
