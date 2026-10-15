def reference(head):
    # Count first, then walk to the middle (the second middle when the length is even).
    values = []
    while head is not None:
        values.append(head.val)
        head = head.next
    return values[len(values) // 2 :]
