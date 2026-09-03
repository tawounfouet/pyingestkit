from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from rich.markup import escape

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
    return str(getattr(record, "log_context", ""))


class PlainTerminalFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = _terminal_timestamp(record)
        level = f"{record.levelname:<8}"
        context = _context(record)
        spacer = f" {context}" if context else ""
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return f"{timestamp}  {level}{spacer} {message}".rstrip()


class RichTerminalFormatter(logging.Formatter):
    """Rich markup formatter matching the stable human terminal convention."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = escape(_terminal_timestamp(record))
        level = record.levelname
        style = _LEVEL_STYLES.get(level, "white")
        context = escape(_context(record))
        message = escape(record.getMessage())
        context_part = f" [dim]{context}[/dim]" if context else ""
        rendered = f"[dim]{timestamp}[/dim]  [{style}]{level:<8}[/{style}]{context_part} {message}"
        if record.exc_info:
            rendered += f"\n[red]{escape(self.formatException(record.exc_info))}[/red]"
        return rendered.rstrip()


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter suitable for CI, files, and log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("run_id", "job_id", "step"):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)
