def validate(a, b):
    for xs, name in ((a, "a"), (b, "b")):
        if any(xs[i] > xs[i + 1] for i in range(len(xs) - 1)):
            return f"{name} must be sorted from smallest to largest"
    return None
