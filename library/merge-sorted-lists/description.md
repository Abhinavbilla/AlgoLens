Two linked lists are each sorted. Join them into one sorted list, reusing the existing nodes instead of copying values.

Compare the front nodes of the two lists. The smaller one is the next node of the result, so attach it and step past it in its list. Repeat until one list runs out; whatever is left of the other is already sorted, so attach it whole. A **dummy** node at the start means the very first attach is no different from the rest, which removes a fiddly special case.

Every node is attached once: O(n + m) time and O(1) extra space. It's the merge step of merge sort, done with pointers.
