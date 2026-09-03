from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console

from pyingestkit.config.models import LoggingConfig, LogOutputFormat

from .filters import ContextFilter, RedactingFilter
from .formatters import JsonFormatter, PlainTerminalFormatter, RichTerminalFormatter


class _StableRichHandler(logging.Handler):
    """Rich-backed handler with a stable no-wrap terminal layout."""

    def __init__(self) -> None:
        super().__init__()
        self.console = Console(stderr=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            rendered = self.format(record)
            self.console.print(rendered, markup=True, soft_wrap=True)
        except Exception:  # noqa: BLE001 - logging must never break the ingestion runtime
            self.handleError(record)


def _level(value: str) -> int:
    resolved = logging.getLevelName(value.upper())
    if isinstance(resolved, int):
        return resolved
    raise ValueError(f"Unknown logging level: {value}")


def _attach_common_filters(handler: logging.Handler) -> None:
    handler.addFilter(ContextFilter())
    handler.addFilter(RedactingFilter())


def _console_handler(config: LoggingConfig) -> logging.Handler:
    if config.format is LogOutputFormat.RICH:
        handler: logging.Handler = _StableRichHandler()
        handler.setFormatter(RichTerminalFormatter())
    elif config.format is LogOutputFormat.JSON:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(PlainTerminalFormatter())
    handler.setLevel(_level(config.level))
    _attach_common_filters(handler)
    return handler


def _file_handler(config: LoggingConfig) -> logging.Handler | None:
    file_config = config.file
    if not file_config.enabled:
        return None
    path = Path(file_config.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=file_config.max_bytes,
        backupCount=file_config.backup_count,
        encoding="utf-8",
    )
    handler.setLevel(_level(file_config.level))
    if file_config.format is LogOutputFormat.JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(PlainTerminalFormatter())
    _attach_common_filters(handler)
    return handler


def configure_logging(
    config: LoggingConfig,
    *,
    level_override: str | None = None,
    format_override: LogOutputFormat | None = None,
) -> None:
    """Configure application logging explicitly at the CLI/application boundary."""
    effective = config.model_copy(
        update={
            **({"level": level_override.upper()} if level_override else {}),
            **({"format": format_override} if format_override else {}),
        }
    )
    _level(effective.level)

    root = logging.getLogger()
    for handler in tuple(root.handlers):
        root.removeHandler(handler)
        handler.close()

    active_levels: list[int] = []
    if effective.console:
        root.addHandler(_console_handler(effective))
        active_levels.append(_level(effective.level))
    file_handler = _file_handler(effective)
    if file_handler is not None:
        root.addHandler(file_handler)
        active_levels.append(_level(effective.file.level))
    if not root.handlers:
        root.addHandler(logging.NullHandler())
    root.setLevel(min(active_levels) if active_levels else logging.CRITICAL + 1)

    package_logger = logging.getLogger("pyingestkit")
    package_logger.setLevel(logging.NOTSET)
    package_logger.propagate = True
