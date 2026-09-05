from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from .context import current_log_context

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret)"
        r"\s*([=:])\s*([^\s,;]+)"
    ),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
)
_SECRET_KEY = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret|authorization)"
)
_URL_PASSWORD = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+:)([^@/\s]+)(@)")


def redact_text(value: str) -> str:
    redacted = _URL_PASSWORD.sub(r"\1***REDACTED***\3", value)
    for pattern in _SECRET_PATTERNS:
        if "authorization" in pattern.pattern.lower():
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        else:
            redacted = pattern.sub(r"\1\2***REDACTED***", redacted)
    return redacted


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively redact secret-looking configuration/runtime parameter keys."""
    result: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if _SECRET_KEY.search(key_text):
            result[key_text] = "***REDACTED***"
        elif isinstance(item, Mapping):
            result[key_text] = redact_mapping(item)
        elif isinstance(item, list):
            result[key_text] = [
                redact_mapping(entry) if isinstance(entry, Mapping) else entry for entry in item
            ]
        elif isinstance(item, str):
            result[key_text] = redact_text(item)
        else:
            result[key_text] = item
    return result


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = current_log_context()
        run_id = context["run_id"] or ""
        job_id = context["job_id"] or ""
        step = context["step"] or ""
        record.run_id = run_id
        run_short_id = run_id[:8] if run_id else ""
        record.run_short_id = run_short_id
        record.job_id = job_id
        record.step = step
        parts: list[str] = []
        if run_short_id:
            parts.append(f"run={run_short_id}")
        if job_id:
            parts.append(f"job={job_id}")
        if step:
            parts.append(f"step={step}")
        record.log_context = f"[{' '.join(parts)}]" if parts else ""
        return True


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True
