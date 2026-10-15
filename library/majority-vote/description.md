One value appears more than half the time. Find it using O(1) memory, without counting every value.

Think of it as an election where different values knock each other out in pairs. Keep a candidate and a vote count. A value equal to the candidate adds a vote; a different value removes one, as if the two cancelled out. When the count hits zero, the next value becomes the new candidate.

The majority value has more copies than everything else put together, so it can't be cancelled out completely: it's the candidate left standing at the end. One pass, O(n) time, and just two variables.
