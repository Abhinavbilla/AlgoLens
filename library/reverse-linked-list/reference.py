def reference(head):
    values = []
    while head is not None:
        values.append(head.val)
        head = head.next
    return values[::-1]
