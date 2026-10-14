def rob(nums):
    n = len(nums)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        skip = dp[i - 1]
        take = dp[i - 2] + nums[i - 1] if i >= 2 else nums[i - 1]
        dp[i] = max(skip, take)
    return dp[n]
