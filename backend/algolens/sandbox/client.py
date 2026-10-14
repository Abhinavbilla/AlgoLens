"""Client for the sandbox service, reached over a Unix socket on a shared volume.

The sandbox container has no network at all; this socket is its only way in or out.
"""

from typing import Any

import httpx

from algolens.config import get_settings


class SandboxUnavailable(RuntimeError):
    """The sandbox is down or failed its self-test. Never a verdict on any code."""


# Any failure to reach the socket. httpcore raises RuntimeError for Unix sockets on Windows.
_TRANSPORT_ERRORS = (httpx.HTTPError, OSError, RuntimeError)


class SandboxClient:
    def __init__(self, socket_path: str | None = None, timeout_s: float = 330):
        self._http = httpx.Client(
            transport=httpx.HTTPTransport(uds=socket_path or get_settings().sandbox_socket),
            base_url="http://sandbox",
            timeout=timeout_s,
        )

    def is_healthy(self) -> bool:
        try:
            return self._http.get("/health", timeout=3).status_code == 200
        except _TRANSPORT_ERRORS:
            return False

    def trace(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record one run for animation (see TraceResponse in sandbox/algolens_sandbox/batch.py).
        Raises SandboxUnavailable if the sandbox can't take work at all."""
        return self._post("/v1/trace", request)

    def run_batch(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run a batch (see sandbox/algolens_sandbox/batch.py for the request shape).

        Returns the sandbox's response, whose `status` is ok, compile_error, batch_timeout or
        sandbox_error. Raises SandboxUnavailable if the sandbox can't take work at all.
        """
        return self._post("/v1/batch", request)

    def _post(self, path: str, request: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._http.post(path, json=request)
        except _TRANSPORT_ERRORS as exc:
            raise SandboxUnavailable(f"sandbox unreachable: {exc}") from exc
        if resp.status_code == 503:
            raise SandboxUnavailable(f"sandbox unhealthy: {resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()
