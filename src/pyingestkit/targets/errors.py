from __future__ import annotations

from pyingestkit.core.exceptions import IngestionError


class TargetError(IngestionError):
    """Base class for controlled target-materialization failures."""


class TargetConfigurationError(TargetError):
    """Raised when a target cannot be configured safely."""


class TargetConnectionError(TargetError):
    """Raised when a target connection cannot be opened or checked."""


class TargetLoadError(TargetError):
    """Raised when a dataset cannot be materialized atomically in a target."""


class TargetClosedError(TargetError):
    """Raised when an operation is attempted after a target has been closed."""


class UnsupportedLoadModeError(TargetError):
    """Raised when a backend does not yet implement the requested load mode."""


class InvalidTargetIdentifierError(TargetConfigurationError):
    """Raised when a backend identifier violates the target safety policy."""
