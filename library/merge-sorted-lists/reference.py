def reference(a, b):
    values = []
    for node in (a, b):
        while node is not None:
            values.append(node.val)
            node = node.next
    return sorted(values)
