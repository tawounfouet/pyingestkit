"""Provider-neutral logging primitives.

Human rendering is optional in PyIngestKit 2.0. Importing filters or context
must not require Rich; configure_logging is loaded lazily when requested.
"""

from __future__ import annotations

from typing import Any

from .context import current_log_context, log_context
from .filters import redact_mapping, redact_text

__all__ = [
    "configure_logging",
    "current_log_context",
    "log_context",
    "redact_mapping",
    "redact_text",
]


def __getattr__(name: str) -> Any:
    if name == "configure_logging":
        from .setup import configure_logging

        return configure_logging
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
