You have items, each with a weight and a value, and a bag that holds at most `capacity` weight. Each item is either taken whole or left behind (that's the "0/1"). What's the most value that fits?

Trying every subset of items takes O(2ⁿ) time. Dynamic programming fills a table instead: `dp[i][c]` is the best value using only the first `i` items with room for `c` weight. Row 0 (no items) is all zeros. For item `i` and capacity `c` there are two choices: leave the item, keeping `dp[i - 1][c]`; or, if it fits, take it, which leaves `c - w` room for the earlier items, giving `dp[i - 1][c - w] + v`. The cell keeps the larger. The answer is the bottom-right cell.

It takes O(n × capacity) time and space. Because each row only reads the row above, one row is enough if you fill it from right to left.
