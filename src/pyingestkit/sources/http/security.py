from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_REDACTED = "***REDACTED***"
_SENSITIVE_HEADER = re.compile(
    r"(?i)^(authorization|proxy-authorization|cookie|set-cookie|x-api-key|x-auth-token|"
    r"api-key|apikey|token|x-access-token)$"
)
_SENSITIVE_QUERY = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret|access[_-]?token|auth)"
)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: (_REDACTED if _SENSITIVE_HEADER.match(name.strip()) else value)
        for name, value in headers.items()
    }


def sanitize_url(url: str) -> str:
    """Remove user-info secrets and secret-looking query values from a URL."""

    try:
        parts = urlsplit(url)
    except ValueError:
        return url

    hostname = parts.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = f":{parts.port}" if parts.port is not None else ""
    if parts.username is not None or parts.password is not None:
        netloc = f"{_REDACTED}:{_REDACTED}@{hostname}{port}"
    else:
        netloc = f"{hostname}{port}"

    safe_query = urlencode(
        [
            (key, _REDACTED if _SENSITIVE_QUERY.search(key) else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ],
        doseq=True,
    )
    return urlunsplit((parts.scheme, netloc, parts.path, safe_query, parts.fragment))
