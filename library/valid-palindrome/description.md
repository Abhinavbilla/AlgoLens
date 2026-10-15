A palindrome reads the same forwards and backwards: "level", "abba". Reversing the string and comparing works, but it builds a whole copy.

Instead, put one finger on the first character and one on the last. If they differ, it's not a palindrome. If they match, move both fingers one step inward and compare again. When the fingers meet, every pair has matched.

It's O(n) time and O(1) extra space, and it's the two-pointer pattern in its simplest form: two indexes moving towards each other, each step settling one pair for good.
