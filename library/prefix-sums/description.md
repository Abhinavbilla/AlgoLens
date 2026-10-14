Answer many "what's the sum of positions `l` to `r`?" questions about the same array, quickly.

Adding up each range from scratch costs O(n) per question. Instead, build the *prefix sums* once: `prefix[i]` is the sum of the first `i` values, so `prefix[0]` is 0 and each entry is the previous one plus the next value. Then the sum of positions `l` to `r` is everything up to `r` minus everything before `l`: `prefix[r + 1] - prefix[l]`, one subtraction.

Building the prefix sums takes O(n) time and space, and every query after that takes O(1). The same idea works in two dimensions and underlies many counting problems, such as counting subarrays with a given sum.
