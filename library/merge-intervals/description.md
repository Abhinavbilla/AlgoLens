Given time ranges like meetings, combine every group that overlaps into one range.

Comparing every pair is slow and fiddly. Instead, **sort by start time first**. Now any interval that overlaps the ones before it must overlap the *last* merged interval, so a single left-to-right pass is enough. If the next interval starts before the last merged one ends, stretch that one's end; otherwise, start a new merged interval.

This is a **greedy** algorithm: each step makes the obvious local choice and never revisits it, and the sorting is what makes that safe. It takes O(n log n) time for the sort plus O(n) for the pass. The same "sort, then sweep" idea solves meeting rooms, inserting an interval, and removing the fewest overlapping ones.
