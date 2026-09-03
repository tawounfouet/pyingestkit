from __future__ import annotations

from collections.abc import Mapping

from pyingestkit.core.exceptions import FetchError

from .security import sanitize_url


class HttpError(FetchError):
    """Base class for controlled HTTP acquisition failures."""


class HttpTimeoutError(HttpError):
    def __init__(self, method: str, url: str, timeout_seconds: float) -> None:
        self.method = method
        self.url = url
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"HTTP request timed out: {method} {sanitize_url(url)} timeout={timeout_seconds:.3f}s"
        )


class HttpTransportError(HttpError):
    def __init__(self, method: str, url: str, detail: str) -> None:
        self.method = method
        self.url = url
        self.detail = detail
        super().__init__(f"HTTP transport failed: {method} {sanitize_url(url)}: {detail}")


class HttpStatusError(HttpError):
    def __init__(
        self,
        method: str,
        url: str,
        status_code: int,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.headers = dict(headers or {})
        super().__init__(f"HTTP request failed: {method} {sanitize_url(url)} returned {status_code}")
