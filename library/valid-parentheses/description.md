Brackets are balanced when every opening bracket is closed by the same kind, in the right order: "([])" is fine, "([)]" isn't.

The bracket that must close next is always the most recently opened one, which is exactly what a stack gives you. Read the string left to right. Push every opening bracket. For a closing bracket, the top of the stack must be its partner: pop it if it is, and give up if it isn't (or if the stack is empty). At the end, anything still on the stack was never closed.

One pass, O(n) time, and O(n) space for the stack in the worst case. Editors, compilers and calculators use this same idea every time they check your brackets.
