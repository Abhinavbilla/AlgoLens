You climb a staircase taking one or two steps at a time. In how many different ways can you reach step n?

Think about your **last** move. You arrived at step i either from step i − 1 (a single step) or from step i − 2 (a double step). So the ways to reach step i are the ways to reach i − 1 plus the ways to reach i − 2. That's the whole recurrence, and it's the Fibonacci sequence in disguise.

Solving it from the bottom up, so each answer is computed once and stored in a table, is dynamic programming in its simplest form: O(n) time instead of the exponential time of naive recursion. Only the last two entries are ever needed, so it can even run in O(1) space.
