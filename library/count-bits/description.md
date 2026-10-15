How many 1-bits does a number have in binary? 44 is 101100, so the answer is 3.

You could check all the bit positions one by one, but there's a neater trick. Subtracting 1 from a number flips its lowest 1-bit to 0 and turns every 0 below it into 1: 101100 − 1 = 101011. So `n & (n - 1)` keeps everything except that lowest 1-bit: 101100 & 101011 = 101000. Each step removes exactly one 1-bit, so the number of steps until n reaches 0 is the number of 1-bits.

It takes one step per 1-bit rather than one per bit position (Brian Kernighan's method). The same expression tests whether a number is a power of two: then it has exactly one 1-bit, so `n & (n - 1)` is 0.
