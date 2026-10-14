def range_sums(nums, queries):
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    answers = []
    for l, r in queries:
        answers.append(prefix[r + 1] - prefix[l])
    return answers
