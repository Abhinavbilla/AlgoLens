def count_bits(n):
    count = 0
    while n > 0:
        bits = [int(b) for b in format(n, "b")]
        n = n & (n - 1)
        count += 1
    return count
