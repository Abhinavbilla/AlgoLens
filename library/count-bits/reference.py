def reference(n):
    # Check every bit position directly.
    return sum(1 for k in range(n.bit_length()) if n >> k & 1)
