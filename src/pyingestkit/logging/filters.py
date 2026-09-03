from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from .context import current_log_context

_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\s*([=:])\s*([^\s,;]+)"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
)
_SECRET_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret|authorization)")


def redact_text(value: str) -> str:
    redacted = value
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
        if _SECRET_KEY.search(str(key)):
            result[str(key)] = "***REDACTED***"
        elif isinstance(item, Mapping):
            result[str(key)] = redact_mapping(item)
        elif isinstance(item, list):
            result[str(key)] = [redact_mapping(v) if isinstance(v, Mapping) else v for v in item]
        else:
            result[str(key)] = item
    return result


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = current_log_context()
        record.run_id = context["run_id"] or ""
        record.run_short_id = record.run_id[:8] if record.run_id else ""
        record.job_id = context["job_id"] or ""
        record.step = context["step"] or ""
        parts = []
        if record.run_short_id:
            parts.append(f"run={record.run_short_id}")
        if record.job_id:
            parts.append(f"job={record.job_id}")
        if record.step:
            parts.append(f"step={record.step}")
        record.log_context = f"[{' '.join(parts)}]" if parts else ""
        return True


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True
