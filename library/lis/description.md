Pick values from left to right, skipping any you like, so that they strictly increase. How long can that be? In 3, 1, 4, 1, 5, 9, 2, 6 the answer is 4 (for example 1, 4, 5, 9).

Dynamic programming asks a smaller question for every position: what's the longest increasing run that *ends here*? It's 1 on its own, or one more than the best run ending at some earlier, smaller value. Fill these in left to right, each using the answers before it, and the overall answer is the largest one.

Two nested loops make this O(n²). There's a cleverer O(n log n) version that uses binary search, but this one shows the idea plainly: describe each answer in terms of smaller answers you've already worked out.
