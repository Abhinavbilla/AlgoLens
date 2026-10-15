Find two positions whose values add up to the target. Checking every pair takes O(n²) time, so the question becomes: for each value, has its partner already appeared?

A **hash map** (a `dict` in Python, an `unordered_map` in C++) answers "have I seen this value, and where?" in constant time on average. Walk the array once. For each value, work out the partner it needs, `target - nums[j]`. If the partner is already in the map, you're done. Otherwise, remember this value and its position for the values still to come.

That's one pass: O(n) time, O(n) extra space for the map. The same trade of a little memory for a lot of speed solves counting problems too: duplicates, anagrams and frequencies. If several pairs work, this returns the first one completed while scanning left to right.
