Two words are anagrams when they use exactly the same letters, the same number of times: "listen" and "silent". Sorting both and comparing works, but it takes O(n log n) time.

Counting is faster. Walk the first word and count each letter in a hash map. Then walk the second word and use the letters up: each one must still have a count above zero, or the second word has a letter the first doesn't have enough of. If the words are the same length and nothing runs out, every count ends at zero, so they're anagrams.

Two passes over the words: O(n) time, plus one count per distinct letter. Counting characters like this is the heart of a whole family of string problems: anagrams, permutations in a string, and "first unique character".
