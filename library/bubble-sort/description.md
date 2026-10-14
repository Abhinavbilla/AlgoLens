Bubble sort walks through the array comparing each pair of neighbours and swaps them when they're in the wrong order. After one full pass, the largest value has "bubbled" to the end, so each later pass can stop one position earlier. If a pass makes no swaps at all, the array is sorted and the algorithm stops early.

It takes O(n²) time in the worst case and O(1) extra space. It's rarely used in practice, but it's a clear way to see how comparison sorts make progress one swap at a time.
