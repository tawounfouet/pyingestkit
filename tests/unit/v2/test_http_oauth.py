"""Unit tests for OAuth 2.0 token management, lifecycle automation and secret redaction."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from pyingestkit.adapters.http.oauth import (
    ClientCredentialsOAuthProvider,
    OAuthError,
    OAuthToken,
    OAuthTokenManager,
    RefreshTokenOAuthProvider,
)
from pyingestkit.adapters.http.source import HttpAccessPolicy, HttpSourceConnector
from pyingestkit.adapters.http.transport import (
    HttpRequestV2,
    HttpResponseV2,
)
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.resources import CredentialReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source


class _MockClient:
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.requests: list[HttpRequestV2] = []

    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        self.requests.append(request)
        return self._handler(request)


def _request(
    url: str = "https://api.example.test/protected/data.csv",
    credential: CredentialReference | None = None,
) -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    return AcquisitionRequest(
        source=Source.http(
            url=url,
            credential=credential or CredentialReference("oauth-test", provider="test"),
        ),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )


def test_oauth_token_expiration_and_redaction() -> None:
    token = OAuthToken(
        access_token="secret-access-token-999",
        refresh_token="secret-refresh-token-888",
        expires_at=time.time() + 30.0,
    )
    # With 60s skew, 30s remaining is considered expired
    assert token.is_expired(clock_skew_seconds=60.0) is True
    # With 10s skew, 30s remaining is not expired
    assert token.is_expired(clock_skew_seconds=10.0) is False

    # Check strict redaction
    repr_str = repr(token)
    assert "secret-access-token-999" not in repr_str
    assert "secret-refresh-token-888" not in repr_str
    assert "***REDACTED***" in repr_str


def test_client_credentials_provider_success() -> None:
    def handler(request: HttpRequestV2) -> HttpResponseV2:
        assert request.url == "https://auth.example.test/oauth/token"
        assert request.method == "POST"
        assert b"grant_type=client_credentials" in request.body
        assert b"client_id=my-client-id" in request.body
        assert b"client_secret=my-client-secret" in request.body
        assert b"scope=read+write" in request.body
        return HttpResponseV2(
            200,
            request.url,
            (("Content-Type", "application/json"),),
            json.dumps(
                {
                    "access_token": "token-xyz-123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            ).encode("utf-8"),
        )

    client = _MockClient(handler)
    provider = ClientCredentialsOAuthProvider(
        token_url="https://auth.example.test/oauth/token",
        client_id="my-client-id",
        client_secret="my-client-secret",
        scopes=("read", "write"),
    )

    token = provider.get_token(client)
    assert token.access_token == "token-xyz-123"
    assert token.token_type == "Bearer"
    assert token.expires_at is not None
    assert token.expires_at > time.time() + 3500

    # Ensure provider repr redacts secret
    assert "my-client-secret" not in repr(provider)
    assert "***REDACTED***" in repr(provider)


def test_client_credentials_provider_error() -> None:
    def handler(request: HttpRequestV2) -> HttpResponseV2:
        return HttpResponseV2(
            401,
            request.url,
            (("Content-Type", "application/json"),),
            b'{"error": "invalid_client"}',
        )

    client = _MockClient(handler)
    provider = ClientCredentialsOAuthProvider(
        token_url="https://auth.example.test/oauth/token",
        client_id="my-client-id",
        client_secret="wrong-secret",
    )

    with pytest.raises(OAuthError, match="non-success status: 401"):
        provider.get_token(client)


def test_refresh_token_provider_success_with_rotation() -> None:
    def handler(request: HttpRequestV2) -> HttpResponseV2:
        assert request.url == "https://auth.example.test/oauth/token"
        assert request.method == "POST"
        assert b"grant_type=refresh_token" in request.body
        return HttpResponseV2(
            200,
            request.url,
            (("Content-Type", "application/json"),),
            json.dumps(
                {
                    "access_token": "new-access-token",
                    "token_type": "Bearer",
                    "expires_in": 1800,
                    "refresh_token": "rotated-refresh-token",
                }
            ).encode("utf-8"),
        )

    client = _MockClient(handler)
    provider = RefreshTokenOAuthProvider(
        token_url="https://auth.example.test/oauth/token",
        client_id="app-id",
        refresh_token="initial-refresh-token",
    )

    token = provider.get_token(client)
    assert token.access_token == "new-access-token"
    assert token.refresh_token == "rotated-refresh-token"
    # Ensure next call will use the rotated refresh token
    assert provider._current_refresh_token == "rotated-refresh-token"

    # Redaction test
    assert "initial-refresh-token" not in repr(provider)
    assert "rotated-refresh-token" not in repr(provider)
    assert "***REDACTED***" in repr(provider)


def test_oauth_token_manager_caching_and_invalidation() -> None:
    call_count = 0

    class CountingProvider:
        def get_token(self, client: HttpRequestV2) -> OAuthToken:
            nonlocal call_count
            call_count += 1
            return OAuthToken(
                access_token=f"token-{call_count}",
                expires_at=time.time() + 3600.0,
            )

        def invalidate(self) -> None:
            pass

    client = _MockClient(lambda req: HttpResponseV2(200, req.url, (), b""))
    manager = OAuthTokenManager(provider=CountingProvider())

    # First call: fetches from provider
    header1 = manager.get_authorization_header(client)
    assert header1 == ("Authorization", "Bearer token-1")
    assert call_count == 1

    # Second call: served from cache
    header2 = manager.get_authorization_header(client)
    assert header2 == ("Authorization", "Bearer token-1")
    assert call_count == 1

    # Invalidate cache
    manager.invalidate()
    header3 = manager.get_authorization_header(client)
    assert header3 == ("Authorization", "Bearer token-2")
    assert call_count == 2


def test_http_connector_auto_refreshes_token_on_401() -> None:
    api_calls = 0

    def handler(request: HttpRequestV2) -> HttpResponseV2:
        nonlocal api_calls
        if "oauth/token" in request.url:
            return HttpResponseV2(
                200,
                request.url,
                (("Content-Type", "application/json"),),
                json.dumps(
                    {
                        "access_token": f"token-v{api_calls + 1}",
                        "expires_in": 3600,
                    }
                ).encode("utf-8"),
            )
        # Protected API
        api_calls += 1
        auth_header = dict(request.headers).get("Authorization")
        if auth_header == "Bearer token-v1":
            # First attempt with expired token: returns 401
            return HttpResponseV2(401, request.url, (), b"Unauthorized")
        # Second attempt with refreshed token: returns 200
        assert auth_header == "Bearer token-v2"
        return HttpResponseV2(200, request.url, (), b"id,val\n1,success\n")

    client = _MockClient(handler)
    provider = ClientCredentialsOAuthProvider(
        token_url="https://api.example.test/oauth/token",
        client_id="saas-client",
        client_secret="saas-secret",
    )
    oauth_manager = OAuthTokenManager(provider=provider)

    policy = HttpAccessPolicy(
        allowed_hosts=("api.example.test",),
        retry_backoff_seconds=0.0,
    )
    connector = HttpSourceConnector(
        policy=policy,
        client=client,
        oauth_manager=oauth_manager,
    )

    result = connector.acquire(_request("https://api.example.test/protected/data.csv"))
    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.content == b"id,val\n1,success\n"
    # Should have called: token endpoint (1), API (401), token endpoint (2), API (200)
    assert api_calls == 2
