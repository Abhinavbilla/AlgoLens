A row of houses holds some money each, and you can't take from two neighbouring houses. What's the most you can collect?

Trying every allowed set of houses takes exponential time. Dynamic programming instead builds the answer for longer and longer prefixes of the row. Let `dp[i]` be the best total from the first `i` houses. For house `i` there are only two choices: skip it, and keep `dp[i - 1]`; or take it, which rules out its left neighbour, giving its money plus `dp[i - 2]`. The better of the two is `dp[i]`.

Each house is looked at once, so it takes O(n) time. The table uses O(n) space, though only the last two entries are ever needed, so it can be cut to O(1).
