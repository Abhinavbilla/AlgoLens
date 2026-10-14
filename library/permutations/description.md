List every ordering of a set of distinct values.

Backtracking builds one arrangement at a time. The current arrangement, `path`, grows one position at a time: at each step, try every value that isn't used yet, place it, and recurse to fill the remaining positions. When `path` holds every value, it's a complete permutation, so it's recorded. On the way back out, the value is removed and marked free again, so the next choice starts from exactly the same state. That undo step is what makes it backtracking.

There are n! permutations and each takes O(n) to copy, so it takes O(n · n!) time. Apart from the output, it uses O(n) space for the path, the used flags and the call stack. Watch the call stack: its depth is the number of values placed so far.
