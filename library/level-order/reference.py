def reference(root):
    # Depth-first instead of a queue: put each value in the list for its depth.
    levels = []

    def walk(node, depth):
        if node is None:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)

    walk(root, 0)
    return levels
