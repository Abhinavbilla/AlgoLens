Selection sort fills the array one position at a time. For position 0 it scans the whole array for the smallest value and swaps it there. For position 1 it does the same with what's left, and so on. Everything to the left of the current position is sorted and final.

It always makes about n²/2 comparisons, even on an array that's already sorted, but at most n swaps, which is handy when writing values is expensive. It uses O(1) extra space. It isn't stable: a swap can jump an item over an equal one.
