def postorder(root):
    order = []

    def visit(node):
        if node is None:
            return
        visit(node.left)
        visit(node.right)
        order.append(node.val)

    visit(root)
    return order
