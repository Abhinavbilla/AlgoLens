def next_greater(nums):
    answer = [-1] * len(nums)
    stack = []
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] < x:
            j = stack.pop()
            answer[j] = x
        stack.append(i)
    return answer
