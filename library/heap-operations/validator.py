def validate(ops):
    # A pop needs something to pop.
    size = 0
    for k, op in enumerate(ops):
        if op[0] == "push":
            size += 1
        elif size == 0:
            return f"operation {k} pops from an empty heap"
        else:
            size -= 1
    return None
