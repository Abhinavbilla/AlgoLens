def preorder(root):
    order = []

    def visit(node):
        if node is None:
            return
        order.append(node.val)
        visit(node.left)
        visit(node.right)

    visit(root)
    return order
