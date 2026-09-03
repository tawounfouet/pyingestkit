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
