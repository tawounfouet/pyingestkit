"""Dependency-neutral HTTP transport values for the V2 HTTP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pyingestkit.domain.shared.validation import require_non_blank


class HttpTransportErrorV2(Exception):
    """Base transport failure raised by an HTTP client adapter."""


class HttpTimeoutErrorV2(HttpTransportErrorV2):
    """The HTTP exchange exceeded its configured timeout."""


class HttpResponseTooLargeErrorV2(Exception):
    """The HTTP body exceeded the acquisition byte limit."""


@dataclass(frozen=True, slots=True)
class HttpRequestV2:
    """One dependency-neutral HTTP request issued by HttpSourceConnector."""

    url: str
    headers: tuple[tuple[str, str], ...] = ()
    timeout_seconds: float = 30.0
    max_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        require_non_blank(self.url, "HttpRequestV2 url")
        if not isinstance(self.headers, tuple):
            raise TypeError("HttpRequestV2 headers must be a tuple.")
        seen: set[str] = set()
        for item in self.headers:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("HttpRequestV2 headers must contain key/value pairs.")
            name, value = item
            require_non_blank(name, "HttpRequestV2 header name")
            if not isinstance(value, str):
                raise TypeError("HttpRequestV2 header values must be strings.")
            if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
                raise ValueError("HttpRequestV2 headers must not contain CR/LF characters.")
            normalized = name.lower()
            if normalized in seen:
                raise ValueError(f"HttpRequestV2 duplicate header: {name!r}.")
            seen.add(normalized)
        if not isinstance(self.timeout_seconds, (int, float)):
            raise TypeError("HttpRequestV2 timeout_seconds must be numeric.")
        if self.timeout_seconds <= 0:
            raise ValueError("HttpRequestV2 timeout_seconds must be > 0.")
        if not isinstance(self.max_bytes, int):
            raise TypeError("HttpRequestV2 max_bytes must be an int.")
        if self.max_bytes < 1:
            raise ValueError("HttpRequestV2 max_bytes must be >= 1.")


@dataclass(frozen=True, slots=True)
class HttpResponseV2:
    """Dependency-neutral HTTP response evidence kept inside the adapter boundary."""

    status_code: int
    url: str
    headers: tuple[tuple[str, str], ...]
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.status_code, int):
            raise TypeError("HttpResponseV2 status_code must be an int.")
        if not 100 <= self.status_code <= 599:
            raise ValueError("HttpResponseV2 status_code must be between 100 and 599.")
        require_non_blank(self.url, "HttpResponseV2 url")
        if not isinstance(self.headers, tuple):
            raise TypeError("HttpResponseV2 headers must be a tuple.")
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
            for item in self.headers
        ):
            raise TypeError("HttpResponseV2 headers must contain string key/value pairs.")
        if not isinstance(self.content, bytes):
            raise TypeError("HttpResponseV2 content must be bytes.")

    def header(self, name: str) -> str | None:
        """Return the first case-insensitive response header value."""
        needle = name.lower()
        for key, value in self.headers:
            if key.lower() == needle:
                return value
        return None


@runtime_checkable
class HttpClientV2(Protocol):
    """Single-exchange HTTP client port owned by the HTTP adapter."""

    def send(self, request: HttpRequestV2) -> HttpResponseV2: ...
