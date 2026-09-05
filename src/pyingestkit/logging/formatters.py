from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from rich.markup import escape

from .filters import redact_text

_LEVEL_STYLES = {
    "DEBUG": "dim cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "bold red",
    "CRITICAL": "bold white on red",
}


def _terminal_timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _context(record: logging.LogRecord) -> str:
    return str(record.__dict__.get("log_context", ""))


class PlainTerminalFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = _terminal_timestamp(record)
        level = f"{record.levelname:<8}"
        context = _context(record)
        spacer = f" {context}" if context else ""
        message = redact_text(record.getMessage())
        if record.exc_info:
            exception = redact_text(self.formatException(record.exc_info))
            message = f"{message}\n{exception}"
        return f"{timestamp}  {level}{spacer} {message}".rstrip()


class RichTerminalFormatter(logging.Formatter):
    """Rich markup formatter matching the stable human terminal convention."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = escape(_terminal_timestamp(record))
        level = record.levelname
        style = _LEVEL_STYLES.get(level, "white")
        context = escape(_context(record))
        message = escape(redact_text(record.getMessage()))
        context_part = f" [dim]{context}[/dim]" if context else ""
        rendered = f"[dim]{timestamp}[/dim]  [{style}]{level:<8}[/{style}]{context_part} {message}"
        if record.exc_info:
            exception = escape(redact_text(self.formatException(record.exc_info)))
            rendered += f"\n[red]{exception}[/red]"
        return rendered.rstrip()


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter suitable for CI, files, and log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        for key in ("run_id", "job_id", "step"):
            value = record.__dict__.get(key)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)
