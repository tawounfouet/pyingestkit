"""Canonical public exception namespace for PyIngestKit V1.

The classes exported here are the same objects exposed by their historical
sub-packages.  This module improves import ergonomics without changing
exception identity, so existing ``except`` clauses remain compatible.
"""

from pyingestkit.core.exceptions import (
    ConfigurationError,
    DiffError,
    DiscoveryError,
    FetchError,
    HookError,
    IngestionError,
    NormalizationError,
    ParseError,
    PluginError,
    PublicationError,
    ReplayError,
    ReplayIntegrityError,
    ReplayMismatchError,
    SnapshotError,
    StorageError,
    ValidationError,
    VersionStoreError,
)
from pyingestkit.sources.http.exceptions import (
    HttpError,
    HttpStatusError,
    HttpTimeoutError,
    HttpTransportError,
)
from pyingestkit.targets.errors import (
    InvalidTargetIdentifierError,
    TargetClosedError,
    TargetConfigurationError,
    TargetConnectionError,
    TargetError,
    TargetLoadConflictError,
    TargetLoadError,
    UnsupportedLoadModeError,
)

__all__ = [
    "ConfigurationError",
    "DiffError",
    "DiscoveryError",
    "FetchError",
    "HookError",
    "HttpError",
    "HttpStatusError",
    "HttpTimeoutError",
    "HttpTransportError",
    "IngestionError",
    "InvalidTargetIdentifierError",
    "NormalizationError",
    "ParseError",
    "PluginError",
    "PublicationError",
    "ReplayError",
    "ReplayIntegrityError",
    "ReplayMismatchError",
    "SnapshotError",
    "StorageError",
    "TargetClosedError",
    "TargetConfigurationError",
    "TargetConnectionError",
    "TargetError",
    "TargetLoadConflictError",
    "TargetLoadError",
    "UnsupportedLoadModeError",
    "ValidationError",
    "VersionStoreError",
]
