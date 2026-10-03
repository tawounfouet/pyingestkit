"""Clean-slate V2 source and acquisition API during the V1 transition."""

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.adapters.http import (
    HttpAccessPolicy,
    HttpClientV2,
    HttpCredentialResolverV2,
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpSourceConnector,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
)
from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.ports.sources import (
    SourceConnector,
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)

__all__ = [
    "AcquisitionRequest",
    "AcquisitionResult",
    "AcquisitionStatus",
    "FileAccessPolicy",
    "FileSourceConnector",
    "HttpAccessPolicy",
    "HttpClientV2",
    "HttpCredentialResolverV2",
    "HttpRequestV2",
    "HttpResponseTooLargeErrorV2",
    "HttpResponseV2",
    "HttpSourceConnector",
    "HttpTimeoutErrorV2",
    "HttpTransportErrorV2",
    "Source",
    "SourceConnector",
    "SourceConnectorCapability",
    "SourceConnectorDescriptor",
    "SourceKind",
    "SourceRegistry",
]
