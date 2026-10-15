When the values are small whole numbers, you don't need to compare them at all. Make one counter per possible value, walk the array once to count each value, then walk the counters in order and write each value out as many times as it was counted.

That's O(n + k) time, where k is the range of values, and it beats every comparison sort when k is small. The catch is the counters: values from 0 to a billion would need a billion of them. Counting sort is also the building block of radix sort, which sorts large numbers one digit at a time.
