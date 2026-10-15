Find the largest sum of any contiguous run of values. Trying every start and end takes O(n²).

Kadane's insight: walk left to right and keep `current`, the best sum of a run that *ends at the value you're on*. For each new value there are only two choices: add it to the run you have, or start a new run at this value. If the run so far is negative, it can only drag the new value down, so you start fresh. The best `current` seen anywhere is the answer.

One pass, O(n) time and O(1) space. It's also a tiny dynamic programming solution: the best run ending here is built from the best run ending one step earlier.
