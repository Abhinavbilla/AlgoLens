def reference(root):
    # Level by level, without recursion.
    level, count = [root] if root else [], 0
    while level:
        count += 1
        level = [c for node in level for c in (node.left, node.right) if c]
    return count
