import os
n = 0
try:
    while True:
        if os.fork() == 0:
            import time
            time.sleep(30)
            os._exit(0)
        n += 1
except OSError as e:
    print("fork blocked after", n, type(e).__name__, flush=True)
    os._exit(0)
