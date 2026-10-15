Each value says how far you're allowed to jump from that position. Starting at the first position, can you reach the last one?

Trying every sequence of jumps explodes quickly. The greedy view is simpler: walk forward one position at a time and remember only `reach`, the farthest position any jump so far could get you to. Every position up to `reach` is reachable, and each one might push `reach` further. If you ever step onto a position beyond `reach`, nothing could have got you there, so you're stuck.

One pass, O(n) time and O(1) space. Greedy works here because reaching farther never hurts: the farthest reach is all you need to remember.
