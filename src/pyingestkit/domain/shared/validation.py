"""Validation helpers for portable V2 boundary values."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

_SENSITIVE_KEY_FRAGMENTS = (
    "access_key",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "security_token",
    "signature",
    "token",
)

_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "password",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-security-token",
        "x-amz-signature",
    }
)


def require_non_blank(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")


def validate_optional_text(value: str | None, name: str) -> None:
    if value is not None:
        require_non_blank(value, name)


def validate_contract_version(value: str) -> None:
    require_non_blank(value, "contract_version")
    if not value.isdigit():
        raise ValueError("contract_version must contain decimal digits only.")


def validate_metadata(
    metadata: tuple[tuple[str, str], ...],
    *,
    name: str = "metadata",
    credential_safe: bool = True,
) -> None:
    if not isinstance(metadata, tuple):
        raise TypeError(f"{name} must be a tuple.")

    seen: set[str] = set()
    for item in metadata:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
        ):
            raise TypeError(f"{name} must contain string key/value pairs.")

        key, value = item
        require_non_blank(key, f"{name} key")
        if key in seen:
            raise ValueError(f"{name} contains duplicate key {key!r}.")
        seen.add(key)

        if credential_safe and _looks_sensitive(key):
            raise ValueError(f"{name} must not contain credential-like field {key!r}.")

        if not isinstance(value, str):
            raise TypeError(f"{name} values must be strings.")


def validate_aware_datetime(value: datetime | None, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")


def validate_credential_safe_locator(locator: str | None, name: str = "locator") -> None:
    if locator is None:
        return
    require_non_blank(locator, name)

    try:
        parsed = urlsplit(locator)
    except ValueError as exc:
        raise ValueError(f"{name} is not a valid portable locator.") from exc

    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not embed URI user-info credentials.")

    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            raise ValueError(f"{name} must not embed credential-bearing query parameter {key!r}.")


def validate_owner(value: str, expected: str = "pyingestkit") -> None:
    require_non_blank(value, "owner")
    if value != expected:
        raise ValueError(f"owner must be {expected!r} for this PyIngestKit contract.")


def _looks_sensitive(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_").replace(".", "_")
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def validate_text_tuple(values: tuple[str, ...], name: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple.")
    _validate_non_blank_items(values, name)


def _validate_non_blank_items(values: Iterable[str], name: str) -> None:
    for value in values:
        require_non_blank(value, f"{name} item")
