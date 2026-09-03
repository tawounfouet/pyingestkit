from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .security import redact_headers, sanitize_url

QueryValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, QueryValue] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    follow_redirects: bool = True

    def __post_init__(self) -> None:
        method = self.method.strip().upper()
        if not method:
            raise ValueError("HTTP method must not be empty")
        if not self.url.strip():
            raise ValueError("HTTP URL must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))

    @property
    def safe_url(self) -> str:
        return sanitize_url(self.url)

    @property
    def safe_headers(self) -> Mapping[str, str]:
        return MappingProxyType(redact_headers(self.headers))

    def __repr__(self) -> str:
        return (
            "HttpRequest("
            f"method={self.method!r}, url={self.safe_url!r}, headers={dict(self.safe_headers)!r}, "
            f"params={dict(self.params)!r}, timeout_seconds={self.timeout_seconds!r}, "
            f"follow_redirects={self.follow_redirects!r})"
        )
