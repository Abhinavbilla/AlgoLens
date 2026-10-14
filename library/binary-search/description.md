Binary search finds a position in a sorted array by repeatedly halving the range that could still contain the answer. This version is a *lower bound*: it returns the first position whose value is at least the target, which is also where the target would be inserted to keep the array sorted. If every value is smaller, it returns the array's length.

The range is `lo` up to (but not including) `hi`. Each step looks at the middle and throws away the half that can't hold the answer, so it takes O(log n) time and O(1) extra space.
