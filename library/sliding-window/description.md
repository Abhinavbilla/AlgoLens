Find the length of the shortest contiguous run of values whose sum is at least the target, or 0 if there is none. All values are positive.

A sliding window keeps two ends, `left` and `right`, and the sum of everything between them. Each step grows the window by moving `right` one place. As soon as the sum reaches the target, the window is a candidate, so we record its length and then shrink it from the left for as long as the sum stays at or above the target, looking for something shorter.

Because the values are positive, adding a value only raises the sum and removing one only lowers it. That's what makes it safe never to move either end backwards. Each end moves at most n times, so it takes O(n) time and O(1) space, compared with O(n²) for trying every pair of ends.
