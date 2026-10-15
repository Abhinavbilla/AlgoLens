Find the k largest values without sorting everything. Picture tryouts for a team of k: you keep the k best seen so far, and the one to beat is the *weakest* member of the team.

A min-heap of size k keeps exactly that, with the weakest always on top. Push each new value. If the heap grows past k, pop the top: the smallest of the k + 1 can't be among the k largest. At the end the heap holds the k largest values.

Each push and pop costs O(log k), so it's O(n log k) in total, much less than sorting when k is small, and it works on a stream of values you only see once. It's the standard answer to "top k" problems.
