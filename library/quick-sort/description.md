Quick sort picks a *pivot* value and partitions the array around it: everything smaller goes to its left, everything else to its right. The pivot is then in its final position, and the two sides are sorted the same way by recursive calls.

This version uses the last value of each part as the pivot (Lomuto's partition). Position `p` marks where the next smaller value goes; `k` scans the part, and every value smaller than the pivot is swapped into position `p`. Finally the pivot swaps into position `p` itself.

On average it takes O(n log n) time and sorts in place, using only the call stack for extra space. With this pivot choice an already sorted array is the worst case, O(n²), because every partition is as lopsided as possible. Production versions pick the pivot at random or take the median of three to avoid that.
