def reference(nums):
    # Mark every position you can land on, trying every jump from every reachable position.
    ok = [False] * len(nums)
    ok[0] = True
    for i in range(len(nums)):
        if ok[i]:
            for step in range(1, nums[i] + 1):
                if i + step < len(nums):
                    ok[i + step] = True
    return ok[-1]
