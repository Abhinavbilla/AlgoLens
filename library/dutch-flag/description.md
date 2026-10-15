Sort an array containing only 0s, 1s and 2s, in one pass and without extra memory. (Dijkstra named it after the three stripes of the Dutch flag.)

Keep three markers. Everything before `low` is 0, everything after `high` is 2, and `mid` walks through the unknown middle. A 0 at `mid` swaps down to `low`, and both markers move on. A 1 is already in the right zone, so only `mid` moves. A 2 swaps up to `high` and `high` moves in, but `mid` stays put, because the value that just arrived hasn't been looked at yet.

Each step shrinks the unknown middle by one, so it's O(n) time and O(1) space. The same three-way partition makes quick sort fast on arrays with many repeated values.
