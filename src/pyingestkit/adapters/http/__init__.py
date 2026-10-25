"""HTTP adapters for PyIngestKit V2 with SSRF and OAuth protection."""

from pyingestkit.adapters.http._ssrf import (
    AntiSsrfValidator,
    SsrfSecurityError,
)
from pyingestkit.adapters.http.oauth import (
    ClientCredentialsOAuthProvider,
    OAuthError,
    OAuthToken,
    OAuthTokenManager,
    OAuthTokenProvider,
    RefreshTokenOAuthProvider,
)
from pyingestkit.adapters.http.source import (
    HttpAccessPolicy,
    HttpCredentialResolverV2,
    HttpSourceConnector,
)
from pyingestkit.adapters.http.transport import (
    HttpClientV2,
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)

__all__ = [
    "AntiSsrfValidator",
    "ClientCredentialsOAuthProvider",
    "HttpAccessPolicy",
    "HttpClientV2",
    "HttpCredentialResolverV2",
    "HttpRequestV2",
    "HttpResponseTooLargeErrorV2",
    "HttpResponseV2",
    "HttpSourceConnector",
    "HttpTimeoutErrorV2",
    "HttpTransportErrorV2",
    "OAuthError",
    "OAuthToken",
    "OAuthTokenManager",
    "OAuthTokenProvider",
    "RefreshTokenOAuthProvider",
    "SsrfSecurityError",
]
