from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .security import redact_headers, redact_query_params, sanitize_url

QueryValue = str | int | float | bool | None


def _query_value(value: QueryValue) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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
    def effective_url(self) -> str:
        """Requested URL including explicit params, before persistence redaction."""
        parts = urlsplit(self.url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        query.extend((name, _query_value(value)) for name, value in self.params.items())
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment)
        )

    @property
    def safe_url(self) -> str:
        """Persistence/log-safe requested URI including non-secret query parameters."""
        return sanitize_url(self.effective_url)

    @property
    def safe_headers(self) -> Mapping[str, str]:
        return MappingProxyType(redact_headers(self.headers))

    @property
    def safe_params(self) -> Mapping[str, object]:
        return MappingProxyType(redact_query_params(self.params))

    def __repr__(self) -> str:
        return (
            "HttpRequest("
            f"method={self.method!r}, url={self.safe_url!r}, headers={dict(self.safe_headers)!r}, "
            f"params={dict(self.safe_params)!r}, timeout_seconds={self.timeout_seconds!r}, "
            f"follow_redirects={self.follow_redirects!r})"
        )
