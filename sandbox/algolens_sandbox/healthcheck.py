"""Container healthcheck: GET /health over the Unix socket. Exit 0 only when healthy."""

import http.client
import socket
import sys

SOCKET = "/run/sandbox/sandbox.sock"


class UnixHTTPConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect(SOCKET)


def main() -> int:
    try:
        conn = UnixHTTPConnection("sandbox")
        conn.request("GET", "/health")
        return 0 if conn.getresponse().status == 200 else 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
