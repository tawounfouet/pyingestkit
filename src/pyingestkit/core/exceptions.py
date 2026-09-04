class IngestionError(Exception):
    """Base class for controlled ingestion failures."""


class ConfigurationError(IngestionError):
    pass


class DiscoveryError(IngestionError):
    pass


class FetchError(IngestionError):
    pass


class ParseError(IngestionError):
    pass


class NormalizationError(IngestionError):
    pass


class ValidationError(IngestionError):
    pass


class PublicationError(IngestionError):
    pass


class StorageError(IngestionError):
    pass


class PluginError(IngestionError):
    pass


class HookError(IngestionError):
    pass


class DiffError(IngestionError):
    """Raised when a dataset diff cannot be computed deterministically."""


class SnapshotError(IngestionError):
    """Raised when a Dataset snapshot cannot be encoded, verified, or loaded."""


class VersionStoreError(IngestionError):
    """Raised when immutable dataset version storage cannot satisfy its contract."""
