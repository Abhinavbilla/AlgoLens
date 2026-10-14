import heapq


def reference(ops):
    heap, popped = [], []
    for op in ops:
        if op[0] == "push":
            heapq.heappush(heap, op[1])
        else:
            popped.append(heapq.heappop(heap))
    return popped
