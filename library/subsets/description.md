Backtracking builds every answer one choice at a time and undoes each choice once it's fully explored. To list every subset, the helper records the current subset, then for each remaining number it *chooses* it (adds it to the path), *explores* everything that follows from that choice (a recursive call), and *un-chooses* it (removes it again).

The call stack is the heart of it: each active call remembers where it got to, so going back up resumes exactly where that choice was made. There are 2ⁿ subsets, and each one costs up to n to copy, so this takes O(n × 2ⁿ) time.
