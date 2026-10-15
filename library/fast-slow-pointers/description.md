Find the middle node of a linked list in one pass, without counting it first.

Send two pointers down the list from the head: `slow` moves one node at a time, `fast` moves two. When `fast` reaches the end, `slow` has gone exactly half as far, so it's standing on the middle. With an even number of nodes it stops on the second of the two middle nodes. The result is the list from the middle onwards.

This "tortoise and hare" idea is a pattern of its own. The same two pointers detect a cycle (if there's a loop, `fast` eventually laps `slow` and they meet), and find the start of the cycle too. It takes O(n) time and O(1) extra space.
