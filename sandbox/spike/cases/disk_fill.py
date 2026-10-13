written = 0
try:
    with open("/tmp/fill", "wb") as f:
        while True:
            f.write(b"\0" * (1 << 20))
            f.flush()
            written += 1
except OSError as e:
    print("blocked after", written, "MB", type(e).__name__)
