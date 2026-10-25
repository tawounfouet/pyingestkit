"""OAuth 2.0 token management, lifecycle automation and secret redaction."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from urllib.parse import urlencode

from pyingestkit.adapters.http.transport import (
    HttpClientV2,
    HttpRequestV2,
    HttpTransportErrorV2,
)
from pyingestkit.domain.shared.validation import require_non_blank

_REDACTED = "***REDACTED***"


class OAuthError(HttpTransportErrorV2):
    """Base exception for OAuth 2.0 protocol and token acquisition errors."""


@dataclass(frozen=True, slots=True)
class OAuthToken:
    """One immutable OAuth 2.0 access token evidence with bounded expiration."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: float | None = None
    refresh_token: str | None = None
    scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.access_token, "OAuthToken access_token")
        require_non_blank(self.token_type, "OAuthToken token_type")
        if self.expires_at is not None and not isinstance(self.expires_at, (int, float)):
            raise TypeError("OAuthToken expires_at must be numeric.")
        if not isinstance(self.scopes, tuple):
            raise TypeError("OAuthToken scopes must be a tuple of strings.")

    def is_expired(self, clock_skew_seconds: float = 60.0) -> bool:
        """Return True if the token is already expired or near expiration."""
        if self.expires_at is None:
            return False
        return time.time() + clock_skew_seconds >= self.expires_at

    def __repr__(self) -> str:
        expires_repr = f"{self.expires_at:.1f}" if self.expires_at is not None else "None"
        return (
            f"OAuthToken(access_token='{_REDACTED}', token_type={self.token_type!r}, "
            f"expires_at={expires_repr}, has_refresh_token={self.refresh_token is not None})"
        )

    def __str__(self) -> str:
        return self.__repr__()


@runtime_checkable
class OAuthTokenProvider(Protocol):
    """Protocol for fetching and refreshing OAuth 2.0 tokens."""

    def get_token(self, client: HttpClientV2) -> OAuthToken:
        """Fetch a fresh OAuth 2.0 token using the configured grant."""
        ...

    def invalidate(self) -> None:
        """Invalidate any cached token or state."""
        ...


class ClientCredentialsOAuthProvider:
    """OAuth 2.0 Client Credentials Grant provider (RFC 6749 Section 4.4)."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        scopes: Sequence[str] = (),
        extra_params: Sequence[tuple[str, str]] = (),
    ) -> None:
        require_non_blank(token_url, "ClientCredentialsOAuthProvider token_url")
        require_non_blank(client_id, "ClientCredentialsOAuthProvider client_id")
        require_non_blank(client_secret, "ClientCredentialsOAuthProvider client_secret")
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = tuple(scopes)
        self._extra_params = tuple(extra_params)

    @property
    def token_url(self) -> str:
        return self._token_url

    def get_token(self, client: HttpClientV2) -> OAuthToken:
        params: list[tuple[str, str]] = [
            ("grant_type", "client_credentials"),
            ("client_id", self._client_id),
            ("client_secret", self._client_secret),
        ]
        if self._scopes:
            params.append(("scope", " ".join(self._scopes)))
        params.extend(self._extra_params)

        body = urlencode(params).encode("utf-8")
        headers = (
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Accept", "application/json"),
        )
        request = HttpRequestV2(
            url=self._token_url,
            method="POST",
            headers=headers,
            body=body,
            timeout_seconds=30.0,
        )
        response = client.send(request)
        if not 200 <= response.status_code <= 299:
            raise OAuthError(
                f"OAuth token endpoint returned non-success status: {response.status_code}."
            )

        try:
            payload = json.loads(response.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OAuthError("OAuth token endpoint response is not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise OAuthError("OAuth token response payload must be a JSON object.")

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise OAuthError("OAuth token response missing valid 'access_token'.")

        token_type = str(payload.get("token_type") or "Bearer")
        expires_in = payload.get("expires_in")
        expires_at: float | None = None
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            expires_at = time.time() + float(expires_in)

        refresh_token = payload.get("refresh_token")
        if not isinstance(refresh_token, str):
            refresh_token = None

        return OAuthToken(
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            refresh_token=refresh_token,
            scopes=self._scopes,
        )

    def invalidate(self) -> None:
        pass

    def __repr__(self) -> str:
        return (
            f"ClientCredentialsOAuthProvider(token_url={self._token_url!r}, "
            f"client_id={self._client_id!r}, client_secret='{_REDACTED}')"
        )

    def __str__(self) -> str:
        return self.__repr__()


class RefreshTokenOAuthProvider:
    """OAuth 2.0 Refresh Token Grant provider (RFC 6749 Section 6)."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        refresh_token: str,
        *,
        client_secret: str | None = None,
        scopes: Sequence[str] = (),
        extra_params: Sequence[tuple[str, str]] = (),
    ) -> None:
        require_non_blank(token_url, "RefreshTokenOAuthProvider token_url")
        require_non_blank(client_id, "RefreshTokenOAuthProvider client_id")
        require_non_blank(refresh_token, "RefreshTokenOAuthProvider refresh_token")
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._current_refresh_token = refresh_token
        self._scopes = tuple(scopes)
        self._extra_params = tuple(extra_params)
        self._lock = threading.Lock()

    @property
    def token_url(self) -> str:
        return self._token_url

    def get_token(self, client: HttpClientV2) -> OAuthToken:
        with self._lock:
            params: list[tuple[str, str]] = [
                ("grant_type", "refresh_token"),
                ("refresh_token", self._current_refresh_token),
                ("client_id", self._client_id),
            ]
            if self._client_secret is not None:
                params.append(("client_secret", self._client_secret))
            if self._scopes:
                params.append(("scope", " ".join(self._scopes)))
            params.extend(self._extra_params)

            body = urlencode(params).encode("utf-8")
            headers = (
                ("Content-Type", "application/x-www-form-urlencoded"),
                ("Accept", "application/json"),
            )
            request = HttpRequestV2(
                url=self._token_url,
                method="POST",
                headers=headers,
                body=body,
                timeout_seconds=30.0,
            )
            response = client.send(request)
            if not 200 <= response.status_code <= 299:
                raise OAuthError(
                    f"OAuth refresh endpoint returned non-success status: {response.status_code}."
                )

            try:
                payload = json.loads(response.content.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise OAuthError("OAuth refresh response is not valid JSON.") from exc

            if not isinstance(payload, dict):
                raise OAuthError("OAuth refresh response payload must be a JSON object.")

            access_token = payload.get("access_token")
            if not isinstance(access_token, str) or not access_token.strip():
                raise OAuthError("OAuth refresh response missing valid 'access_token'.")

            # Update refresh token if rotated by authorization server
            new_refresh = payload.get("refresh_token")
            if isinstance(new_refresh, str) and new_refresh.strip():
                self._current_refresh_token = new_refresh

            token_type = str(payload.get("token_type") or "Bearer")
            expires_in = payload.get("expires_in")
            expires_at: float | None = None
            if isinstance(expires_in, (int, float)) and expires_in > 0:
                expires_at = time.time() + float(expires_in)

            return OAuthToken(
                access_token=access_token,
                token_type=token_type,
                expires_at=expires_at,
                refresh_token=self._current_refresh_token,
                scopes=self._scopes,
            )

    def invalidate(self) -> None:
        pass

    def __repr__(self) -> str:
        return (
            f"RefreshTokenOAuthProvider(token_url={self._token_url!r}, "
            f"client_id={self._client_id!r}, refresh_token='{_REDACTED}')"
        )

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(slots=True)
class OAuthTokenManager:
    """Thread-safe OAuth 2.0 token manager with bounded in-memory caching."""

    provider: OAuthTokenProvider
    clock_skew_seconds: float = 60.0
    _cached_token: OAuthToken | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.provider, OAuthTokenProvider):
            raise TypeError("OAuthTokenManager provider must implement OAuthTokenProvider.")
        if not isinstance(self.clock_skew_seconds, (int, float)) or self.clock_skew_seconds < 0:
            raise ValueError("OAuthTokenManager clock_skew_seconds must be >= 0.")

    def get_token(self, client: HttpClientV2) -> OAuthToken:
        """Return a valid cached token or acquire a new one."""
        with self._lock:
            if self._cached_token is not None and not self._cached_token.is_expired(
                self.clock_skew_seconds
            ):
                return self._cached_token

            token = self.provider.get_token(client)
            self._cached_token = token
            return token

    def get_authorization_header(self, client: HttpClientV2) -> tuple[str, str]:
        """Return the (Name, Value) authorization header tuple for requests."""
        token = self.get_token(client)
        return "Authorization", f"{token.token_type} {token.access_token}"

    def invalidate(self) -> None:
        """Invalidate the current token in cache."""
        with self._lock:
            self._cached_token = None
            self.provider.invalidate()
