from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .security import redact_headers, sanitize_url


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str] = field(default_factory=dict)
    content: bytes = b""
    url: str = ""
    elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        if not 100 <= self.status_code <= 599:
            raise ValueError(f"Invalid HTTP status code: {self.status_code}")
        if self.elapsed_seconds is not None and self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be >= 0")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type") or self.headers.get("Content-Type")

    @property
    def content_length(self) -> int:
        return len(self.content)

    @property
    def safe_url(self) -> str:
        return sanitize_url(self.url)

    @property
    def safe_headers(self) -> Mapping[str, str]:
        return MappingProxyType(redact_headers(self.headers))

    def __repr__(self) -> str:
        return (
            "HttpResponse("
            f"status_code={self.status_code!r}, url={self.safe_url!r}, "
            f"content_length={self.content_length!r}, elapsed_seconds={self.elapsed_seconds!r})"
        )
