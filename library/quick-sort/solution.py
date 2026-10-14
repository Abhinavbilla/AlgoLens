def quick_sort(arr):
    sort_part(arr, 0, len(arr) - 1)
    return arr

def sort_part(arr, lo, hi):
    if lo >= hi:
        return
    pivot = arr[hi]
    p = lo
    for k in range(lo, hi):
        if arr[k] < pivot:
            arr[p], arr[k] = arr[k], arr[p]
            p += 1
    arr[p], arr[hi] = arr[hi], arr[p]
    sort_part(arr, lo, p - 1)
    sort_part(arr, p + 1, hi)
