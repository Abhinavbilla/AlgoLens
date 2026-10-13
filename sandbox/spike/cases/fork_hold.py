# Fork as many children as allowed and keep them alive, to starve anything sharing the limit.
import os, time
n = 0
try:
    while True:
        if os.fork() == 0:
            time.sleep(8)
            os._exit(0)
        n += 1
except OSError:
    pass
print("holding", n, flush=True)
time.sleep(6)
