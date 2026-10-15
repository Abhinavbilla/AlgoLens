Find the length of the longest stretch of a string with no character repeated. In "abcabcbb" it's 3 ("abc").

Checking every substring is slow. A sliding window keeps a stretch that has no repeats, plus a set of the characters inside it. Each step adds the next character on the right. If that character is already in the window, drop characters from the left until it isn't. The window is always repeat-free, so its length is a candidate answer at every step.

Each character enters and leaves the window at most once, so it's O(n) time. The set gives instant "is this character already in the window?" checks.
