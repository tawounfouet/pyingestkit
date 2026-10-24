"""Filesystem and diagnostic security helpers for PyIngestKit CLI."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyingestkit.cli.exit_codes import ExitCode

REDACTED = "[REDACTED]"

_SENSITIVE_NAME = (
    r"(?:password|passwd|token|secret|api[_-]?key|"
    r"credential|private[_-]?key|client[_-]?secret)"
)

_URI_USERINFO_PASSWORD_PATTERN = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)([^:@/\s]+):([^/@\s]+)@")

_ASSIGNMENT_PATTERN = re.compile(
    rf"""(?ix)
    (
        ["']?{_SENSITIVE_NAME}["']?
        \s*[:=]\s*
    )
    (
        "(?:\\.|[^"])*"
        |
        '(?:\\.|[^'])*'
        |
        [^\s,;]+
    )
    """
)

_BEARER_PATTERN = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)")


class SecurityError(RuntimeError):
    """Raised when a security invariant or path boundary is violated."""

    def __init__(self, message: str, exit_code: ExitCode = ExitCode.SECURITY_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def sanitize_input_path(raw_path: str | Path) -> Path:
    """Validate and sanitize an input path string, rejecting null bytes."""
    path_str = str(raw_path)
    if "\0" in path_str:
        raise SecurityError("Path contains prohibited null-byte character.")
    return Path(path_str)


def assert_path_within_workspace(
    path: str | Path,
    workspace_root: str | Path | None = None,
) -> Path:
    """Resolve canonical path and assert it is strictly within allowed workspace."""
    root = (Path(workspace_root) if workspace_root else Path.cwd()).resolve()
    cleaned = sanitize_input_path(path)
    candidate = cleaned.resolve() if cleaned.is_absolute() else (root / cleaned).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise SecurityError(
            f"Path '{candidate}' escapes the workspace root '{root}'. Access forbidden."
        ) from None

    return candidate


def redact_sensitive_text(text: str) -> str:
    """Mask credentials, passwords, tokens and API keys from CLI output."""
    if not text:
        return text
    redacted = _URI_USERINFO_PASSWORD_PATTERN.sub(rf"\1\2:{REDACTED}@", text)
    redacted = _BEARER_PATTERN.sub(rf"\1{REDACTED}", redacted)
    return _ASSIGNMENT_PATTERN.sub(rf"\1{REDACTED}", redacted)


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively redact secret-looking configuration or parameter mappings."""
    sensitive_key_re = re.compile(rf"(?i){_SENSITIVE_NAME}|authorization")
    result: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if sensitive_key_re.search(key_text):
            result[key_text] = REDACTED
        elif isinstance(item, Mapping):
            result[key_text] = redact_mapping(item)
        elif isinstance(item, list):
            result[key_text] = [
                redact_mapping(entry) if isinstance(entry, Mapping) else entry for entry in item
            ]
        elif isinstance(item, str):
            result[key_text] = redact_sensitive_text(item)
        else:
            result[key_text] = item
    return result


__all__ = [
    "REDACTED",
    "SecurityError",
    "assert_path_within_workspace",
    "redact_mapping",
    "redact_sensitive_text",
    "sanitize_input_path",
]
