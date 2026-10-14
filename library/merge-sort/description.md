Merge sort is divide and conquer. It splits the array in half, sorts each half by calling itself, and then merges the two sorted halves into one. A part with one value or none is already sorted, which is where the recursion stops.

Merging is the key step: look at the front of each half, take the smaller value, and repeat. When one half runs out, whatever is left of the other is already in order and goes on the end. Taking from the left half when the fronts are equal keeps the sort stable.

The array is halved about log₂ n times and each level of merging touches every value once, so it takes O(n log n) time in every case. The merged copies need O(n) extra space. Watch the call stack: each call works on its own part of the array.
