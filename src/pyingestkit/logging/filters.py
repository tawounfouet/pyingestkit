from __future__ import annotations

import logging
import re

from .context import current_log_context

_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|client[_-]?secret)\s*([=:])\s*([^\s,;]+)"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        if "authorization" in pattern.pattern.lower():
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        else:
            redacted = pattern.sub(r"\1\2***REDACTED***", redacted)
    return redacted


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = current_log_context()
        record.run_id = context["run_id"] or ""
        record.job_id = context["job_id"] or ""
        record.step = context["step"] or ""
        parts = []
        if record.run_id:
            parts.append(f"run={record.run_id}")
        if record.job_id:
            parts.append(f"job={record.job_id}")
        if record.step:
            parts.append(f"step={record.step}")
        record.log_context = f"[{' '.join(parts)}] " if parts else ""
        return True


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Resolve %-style args once, redact the final message, then clear args so
        # downstream handlers all see the same safe text.
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True
