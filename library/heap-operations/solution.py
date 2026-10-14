def heap_ops(ops):
    heap = []
    popped = []
    for op in ops:
        if op[0] == "push":
            heap.append(op[1])
            i = len(heap) - 1
            while i > 0 and heap[(i - 1) // 2] > heap[i]:
                parent = (i - 1) // 2
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
        else:
            popped.append(heap[0])
            last = heap.pop()
            if heap:
                heap[0] = last
                i = 0
                while True:
                    smallest = i
                    for child in (2 * i + 1, 2 * i + 2):
                        if child < len(heap) and heap[child] < heap[smallest]:
                            smallest = child
                    if smallest == i:
                        break
                    heap[i], heap[smallest] = heap[smallest], heap[i]
                    i = smallest
    return popped
