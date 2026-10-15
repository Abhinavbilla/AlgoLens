List every way to choose k different numbers from 1 to n, ignoring order: from 1 to 4, choosing 2 gives [1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4].

Backtracking builds one choice at a time. The current selection is `path`. To extend it, try each number bigger than the last one chosen (that's what `start` is for, so [2, 1] never appears as a copy of [1, 2]), recurse to choose the rest, then remove the number again and try the next. When `path` holds k numbers it's a complete combination.

There are C(n, k) combinations, and each takes O(k) to copy. Watch the call stack: its depth is how many numbers are chosen so far, and every pop of `path` is the "undo" that gives backtracking its name.
