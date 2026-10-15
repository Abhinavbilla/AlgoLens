A linked list is a chain of nodes: each node holds a value and a pointer, `next`, to the node after it. Reversing it means turning every arrow around, without copying the values.

Walk along the list with two pointers. `prev` is the part already reversed (it starts empty) and `curr` is the next node to handle. For each node: remember where the rest of the list is (`nxt`), point the node back at `prev`, and move both pointers one step on. When `curr` falls off the end, `prev` is the head of the reversed list.

Saving `nxt` first is the whole trick. Once `curr.next` is overwritten, the rest of the list would otherwise be lost. It takes O(n) time and O(1) extra space, and it's the warm-up for many linked-list interview questions.
