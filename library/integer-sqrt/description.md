Binary search isn't only for finding things in arrays. Whenever you can check a guess ("is the answer at least this big?") and the answers line up so that every guess below the true answer passes and every guess above fails, you can binary search over the answers themselves.

Here the question is the largest whole number whose square is at most `x`. Every candidate from 0 to x is possible at first. Try the middle one: if its square still fits, the answer is at least that big; if not, it's smaller. Each check halves the range, so it takes O(log x) steps.

This "binary search on the answer" pattern turns many hard-looking problems (smallest capacity, fastest speed, least maximum) into a loop of easy yes-or-no checks.
