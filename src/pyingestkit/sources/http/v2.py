"""Qualified V2 HTTP acquisition API during the V1 transition."""

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

__all__ = [
    "HttpAccessPolicy",
    "HttpClientV2",
    "HttpCredentialResolverV2",
    "HttpRequestV2",
    "HttpResponseTooLargeErrorV2",
    "HttpResponseV2",
    "HttpSourceConnector",
    "HttpTimeoutErrorV2",
    "HttpTransportErrorV2",
]
