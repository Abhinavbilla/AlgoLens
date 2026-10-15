To find a word in a dictionary you don't read every page: you open it in the middle, see whether your word comes before or after, and repeat on that half. Binary search does exactly that on a sorted array.

Keep a range of positions that could still hold the target, `lo` to `hi`. Look at the middle value. If it's the target, you're done. If it's too small, the target can only be to its right, so the whole left half is thrown away in one step; if it's too big, the right half goes. When the range is empty, the target isn't there.

Each step halves the range, so even a million values need only about 20 looks: O(log n). It only works because the array is sorted, which is why "sorted" in a problem is such a strong hint.
