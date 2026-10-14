Insertion sort builds the sorted array one value at a time, the way many people sort a hand of cards. Everything to the left of position `i` is already sorted. It picks up the next value, the *key*, and shifts every larger value one place to the right until it finds where the key belongs, then drops it into the gap.

It takes O(n²) time in the worst case (a reversed array) but only O(n) when the input is already nearly sorted, because each key moves only a short way. It uses O(1) extra space and is stable: equal values keep their order.
