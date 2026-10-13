# Every attempt must fail: public internet, DNS, and sibling containers.
import socket
targets = [("1.1.1.1", 53), ("8.8.8.8", 443), ("db", 5432), ("host.docker.internal", 80)]
for host, port in targets:
    try:
        socket.create_connection((host, port), timeout=2).close()
        print("REACHED", host, port)
    except OSError as e:
        print("blocked", host, port, type(e).__name__)
