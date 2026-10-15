What's the fewest coins that add up to an amount, if you have unlimited coins of each value? Always grabbing the biggest coin doesn't work: with coins 1, 3 and 4, it makes 6 as 4 + 1 + 1, three coins, but 3 + 3 needs only two.

Dynamic programming solves every smaller amount first. `dp[a]` is the fewest coins for amount `a`, and `dp[0]` is 0. For each amount, try each coin `c` as the last coin: the rest, `a - c`, has already been solved, so that option costs `dp[a - c] + 1`. Keep the smallest. An amount no combination can make stays at the "impossible" marker, and the answer for it is -1.

There are `amount` table cells and each tries every coin, so it takes O(amount × coins) time and O(amount) space. It's the classic example of turning "try every combination" into "reuse the answers you already have".
