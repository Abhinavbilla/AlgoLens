The *next greater element* of a value is the first value to its right that's bigger. Checking everything to the right of every value takes O(n²) time. A stack does it in one pass.

The stack holds the positions still waiting for an answer, and their values only go down from bottom to top: a *monotonic* stack. When a new value arrives, it answers every waiting value smaller than itself. Those get popped, and then the new value waits too. Each position is pushed and popped at most once, so the whole thing takes O(n) time.
