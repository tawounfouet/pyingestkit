"""Secure synchronous HTTP source connector for PyIngestKit V2 with SSRF and OAuth hardening."""

from __future__ import annotations

import hashlib
import importlib.util
import ipaddress
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from pyingestkit.adapters.http._ssrf import AntiSsrfValidator, SsrfSecurityError
from pyingestkit.adapters.http.oauth import OAuthError, OAuthTokenManager
from pyingestkit.adapters.http.transport import (
    _ALLOWED_HTTP_METHODS,
    HttpClientV2,
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
)
from pyingestkit.domain.resources import CredentialReference, ResourceReference
from pyingestkit.domain.runtime import (
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.sources import SourceKind
from pyingestkit.ports.sources import (
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_DEFAULT_RETRY_STATUSES = (408, 425, 429, 500, 502, 503, 504)
_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "password",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-security-token",
        "x-amz-signature",
    }
)


@dataclass(frozen=True, slots=True)
class HttpAccessPolicy:
    """Explicit network boundary for HTTP acquisition."""

    allowed_hosts: tuple[str, ...]
    max_bytes: int = 128 * 1024 * 1024
    timeout_seconds: float = 30.0
    max_redirects: int = 5
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    max_retry_after_seconds: float = 60.0
    retry_statuses: tuple[int, ...] = _DEFAULT_RETRY_STATUSES
    allow_http: bool = False
    allowed_ports: tuple[int, ...] = ()
    allow_private_networks: bool = False
    allowed_ip_ranges: tuple[str, ...] = ()
    retry_jitter: bool = True
    max_backoff_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_hosts, tuple):
            raise TypeError("HttpAccessPolicy allowed_hosts must be a tuple.")
        if not self.allowed_hosts:
            raise ValueError("HttpAccessPolicy requires at least one allowed host.")
        normalized: set[str] = set()
        for host in self.allowed_hosts:
            if not isinstance(host, str) or not host.strip():
                raise ValueError("HttpAccessPolicy hosts must be non-blank strings.")
            candidate = host.strip().lower().rstrip(".")
            if "://" in candidate or "/" in candidate or "@" in candidate:
                raise ValueError("HttpAccessPolicy hosts must be hostnames, not URLs.")
            if candidate in normalized:
                raise ValueError("HttpAccessPolicy allowed_hosts must be unique.")
            normalized.add(candidate)
        if not isinstance(self.max_bytes, int) or self.max_bytes < 1:
            raise ValueError("HttpAccessPolicy max_bytes must be an int >= 1.")
        if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ValueError("HttpAccessPolicy timeout_seconds must be > 0.")
        if not isinstance(self.max_redirects, int) or self.max_redirects < 0:
            raise ValueError("HttpAccessPolicy max_redirects must be an int >= 0.")
        if not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValueError("HttpAccessPolicy max_attempts must be an int >= 1.")
        if (
            not isinstance(self.retry_backoff_seconds, (int, float))
            or self.retry_backoff_seconds < 0
        ):
            raise ValueError("HttpAccessPolicy retry_backoff_seconds must be >= 0.")
        if (
            not isinstance(self.max_retry_after_seconds, (int, float))
            or self.max_retry_after_seconds < 0
        ):
            raise ValueError("HttpAccessPolicy max_retry_after_seconds must be >= 0.")
        if not isinstance(self.retry_statuses, tuple):
            raise TypeError("HttpAccessPolicy retry_statuses must be a tuple.")
        if any(
            not isinstance(status, int) or not 100 <= status <= 599
            for status in self.retry_statuses
        ):
            raise ValueError("HttpAccessPolicy retry_statuses must contain valid HTTP statuses.")
        if len(set(self.retry_statuses)) != len(self.retry_statuses):
            raise ValueError("HttpAccessPolicy retry_statuses must be unique.")
        if not isinstance(self.allow_http, bool):
            raise TypeError("HttpAccessPolicy allow_http must be bool.")
        if not isinstance(self.allowed_ports, tuple):
            raise TypeError("HttpAccessPolicy allowed_ports must be a tuple.")
        if any(not isinstance(port, int) or not 1 <= port <= 65535 for port in self.allowed_ports):
            raise ValueError("HttpAccessPolicy allowed_ports must contain valid TCP ports.")
        if len(set(self.allowed_ports)) != len(self.allowed_ports):
            raise ValueError("HttpAccessPolicy allowed_ports must be unique.")
        if not isinstance(self.allow_private_networks, bool):
            raise TypeError("HttpAccessPolicy allow_private_networks must be bool.")
        if not isinstance(self.allowed_ip_ranges, tuple):
            raise TypeError("HttpAccessPolicy allowed_ip_ranges must be a tuple.")
        for cidr in self.allowed_ip_ranges:
            if not isinstance(cidr, str) or not cidr.strip():
                raise ValueError("HttpAccessPolicy allowed_ip_ranges must be non-blank CIDRs.")
            try:
                ipaddress.ip_network(cidr.strip(), strict=False)
            except ValueError as exc:
                raise ValueError(f"HttpAccessPolicy invalid CIDR range: {cidr!r}.") from exc
        if len(set(self.allowed_ip_ranges)) != len(self.allowed_ip_ranges):
            raise ValueError("HttpAccessPolicy allowed_ip_ranges must be unique.")
        if not isinstance(self.retry_jitter, bool):
            raise TypeError("HttpAccessPolicy retry_jitter must be bool.")
        if not isinstance(self.max_backoff_seconds, (int, float)) or self.max_backoff_seconds < 0:
            raise ValueError("HttpAccessPolicy max_backoff_seconds must be >= 0.")

    @property
    def normalized_hosts(self) -> frozenset[str]:
        return frozenset(host.strip().lower().rstrip(".") for host in self.allowed_hosts)


class HttpCredentialResolverV2:
    """Small injectable adapter for turning credential references into request headers."""

    def __init__(
        self,
        resolver: Callable[[CredentialReference], Mapping[str, str]],
    ) -> None:
        if not callable(resolver):
            raise TypeError("HttpCredentialResolverV2 resolver must be callable.")
        self._resolver = resolver

    def headers_for(self, credential: CredentialReference) -> tuple[tuple[str, str], ...]:
        values = self._resolver(credential)
        if not isinstance(values, Mapping):
            raise TypeError("HTTP credential resolver must return a mapping.")
        headers: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name, value in values.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("HTTP credential header names must be non-blank strings.")
            if not isinstance(value, str):
                raise TypeError("HTTP credential header values must be strings.")
            if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
                raise ValueError("HTTP credential headers must not contain CR/LF characters.")
            normalized = name.lower()
            if normalized in seen:
                raise ValueError("HTTP credential resolver returned duplicate headers.")
            seen.add(normalized)
            headers.append((name, value))
        return tuple(headers)


def _extract_http_options(
    request: AcquisitionRequest,
) -> tuple[str, bytes]:
    """Extract HTTP method and body payload non-invasively from request source metadata."""
    method = "GET"
    body = b""
    if request.source.metadata:
        for key, value in request.source.metadata:
            norm_key = key.strip().lower()
            if norm_key in {"http_method", "method"}:
                method = value.strip().upper()
            elif norm_key in {"http_payload", "body", "payload"}:
                body = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    return method, body


class HttpSourceConnector:
    """Acquire one HTTP(S) resource into bounded, secret-safe V2 evidence with SSRF & OAuth protection."""

    def __init__(
        self,
        *,
        policy: HttpAccessPolicy,
        client: HttpClientV2 | None = None,
        credential_resolver: HttpCredentialResolverV2 | None = None,
        oauth_manager: OAuthTokenManager | None = None,
        validator: AntiSsrfValidator | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(policy, HttpAccessPolicy):
            raise TypeError("HttpSourceConnector policy must be HttpAccessPolicy.")
        if client is not None and not isinstance(client, HttpClientV2):
            raise TypeError("HttpSourceConnector client must implement HttpClientV2.")
        if credential_resolver is not None and not isinstance(
            credential_resolver,
            HttpCredentialResolverV2,
        ):
            raise TypeError(
                "HttpSourceConnector credential_resolver must be HttpCredentialResolverV2."
            )
        if oauth_manager is not None and not isinstance(oauth_manager, OAuthTokenManager):
            raise TypeError("HttpSourceConnector oauth_manager must be OAuthTokenManager.")
        if validator is not None and not isinstance(validator, AntiSsrfValidator):
            raise TypeError("HttpSourceConnector validator must be AntiSsrfValidator.")
        if not callable(sleep):
            raise TypeError("HttpSourceConnector sleep must be callable.")
        self._policy = policy
        self._client = client
        self._credential_resolver = credential_resolver
        self._oauth_manager = oauth_manager
        self._validator = validator or AntiSsrfValidator(
            allow_private_networks=policy.allow_private_networks,
            allowed_ip_ranges=policy.allowed_ip_ranges,
        )
        self._sleep = sleep

    @property
    def descriptor(self) -> SourceConnectorDescriptor:
        return SourceConnectorDescriptor(
            id="pyingestkit.http",
            display_name="HTTP(S)",
            connector_version="1",
            supported_source_kinds=(SourceKind.HTTP,),
            capabilities=(SourceConnectorCapability.ACQUIRE,),
            optional_dependencies_available=(
                self._client is not None or importlib.util.find_spec("httpx") is not None
            ),
        )

    @property
    def policy(self) -> HttpAccessPolicy:
        return self._policy

    @property
    def validator(self) -> AntiSsrfValidator:
        return self._validator

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        if not isinstance(request, AcquisitionRequest):
            raise TypeError("HttpSourceConnector.acquire expects AcquisitionRequest.")
        if request.source.kind is not SourceKind.HTTP:
            raise ValueError("HttpSourceConnector only supports SourceKind.HTTP.")
        if request.source.locator is None:
            raise ValueError("HTTP Source requires a locator.")

        method, body = _extract_http_options(request)
        if method not in _ALLOWED_HTTP_METHODS:
            return self._failed(
                request,
                code="acquisition.http.invalid_method",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary=f"HTTP source method {method!r} is not supported.",
            )

        validation_failure = self._validate_url(request.source.locator)
        if validation_failure is not None:
            return self._failed(
                request,
                code=validation_failure[0],
                category=validation_failure[1],
                retryability=Retryability.NON_RETRYABLE,
                summary=validation_failure[2],
            )

        parsed_initial = urlsplit(request.source.locator)
        initial_host = parsed_initial.hostname or ""
        initial_port = parsed_initial.port or (
            443 if parsed_initial.scheme.lower() == "https" else 80
        )
        try:
            resolved_ips = self._validator.resolve_and_validate(initial_host, initial_port)
            pinned_ip = resolved_ips[0]
        except SsrfSecurityError as exc:
            return self._failed(
                request,
                code="acquisition.http.ssrf_blocked",
                category=FailureCategory.AUTHORIZATION,
                retryability=Retryability.NON_RETRYABLE,
                summary=f"HTTP source destination violates anti-SSRF policy: {exc}",
            )

        client, owns_client = self._client_for_acquisition()
        if client is None:
            return self._failed(
                request,
                code="acquisition.http.dependency_missing",
                category=FailureCategory.CAPABILITY,
                retryability=Retryability.NON_RETRYABLE,
                summary="HTTP acquisition requires the HTTPX transport dependency.",
            )

        try:
            headers = self._credential_headers(request, client)
        except (TypeError, ValueError):
            if owns_client:
                self._close_client(client)
            return self._failed(
                request,
                code="acquisition.http.credential_resolution_failed",
                category=FailureCategory.AUTHENTICATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="HTTP credentials could not be resolved into request headers.",
            )

        requested_url, _ = _sanitize_url_for_persistence(request.source.locator)
        current_url = request.source.locator
        redirect_count = 0
        total_attempts = 0
        response: HttpResponseV2 | None = None
        oauth_refreshed = False

        try:
            while True:
                response, attempts = self._send_with_retry(
                    client,
                    current_url,
                    method,
                    body,
                    headers,
                    pinned_ip=pinned_ip,
                )
                total_attempts += attempts

                # Handle OAuth 401 automatic token refresh and single retry
                if (
                    response.status_code == 401
                    and self._oauth_manager is not None
                    and not oauth_refreshed
                ):
                    oauth_refreshed = True
                    self._oauth_manager.invalidate()
                    try:
                        headers = self._credential_headers(request, client)
                        continue
                    except (OAuthError, HttpTransportErrorV2, RuntimeError):
                        return self._status_failure(request, response)

                if response.status_code in _REDIRECT_STATUSES:
                    location = response.header("location")
                    if location is None:
                        return self._failed(
                            request,
                            code="acquisition.http.redirect_missing_location",
                            category=FailureCategory.EXTERNAL_PROVIDER,
                            retryability=Retryability.NON_RETRYABLE,
                            summary="HTTP redirect response did not provide a Location header.",
                        )
                    if redirect_count >= self._policy.max_redirects:
                        return self._failed(
                            request,
                            code="acquisition.http.too_many_redirects",
                            category=FailureCategory.EXTERNAL_PROVIDER,
                            retryability=Retryability.NON_RETRYABLE,
                            summary="HTTP acquisition exceeded the configured redirect limit.",
                        )
                    next_url = urljoin(current_url, location)
                    redirect_failure = self._validate_url(next_url)
                    if redirect_failure is not None:
                        return self._failed(
                            request,
                            code="acquisition.http.redirect_forbidden",
                            category=FailureCategory.AUTHORIZATION,
                            retryability=Retryability.NON_RETRYABLE,
                            summary="HTTP redirect target is outside the configured network policy.",
                        )

                    next_parsed = urlsplit(next_url)
                    next_host = next_parsed.hostname or ""
                    next_port = next_parsed.port or (
                        443 if next_parsed.scheme.lower() == "https" else 80
                    )
                    try:
                        next_resolved = self._validator.resolve_and_validate(next_host, next_port)
                        pinned_ip = next_resolved[0]
                    except SsrfSecurityError:
                        return self._failed(
                            request,
                            code="acquisition.http.redirect_forbidden",
                            category=FailureCategory.AUTHORIZATION,
                            retryability=Retryability.NON_RETRYABLE,
                            summary="HTTP redirect target violates anti-SSRF policy.",
                        )

                    current_url = next_url
                    redirect_count += 1
                    continue

                if not 200 <= response.status_code <= 299:
                    return self._status_failure(request, response)
                break
        except HttpResponseTooLargeErrorV2:
            return self._failed(
                request,
                code="acquisition.http.too_large",
                category=FailureCategory.RESOURCE_EXHAUSTED,
                retryability=Retryability.NON_RETRYABLE,
                summary="HTTP response exceeds the configured acquisition byte limit.",
            )
        except SsrfSecurityError as exc:
            return self._failed(
                request,
                code="acquisition.http.ssrf_blocked",
                category=FailureCategory.AUTHORIZATION,
                retryability=Retryability.NON_RETRYABLE,
                summary=f"HTTP source destination violates anti-SSRF policy: {exc}",
            )
        except HttpTimeoutErrorV2:
            uncertainty = (
                OutcomeUncertainty.REQUIRES_RECONCILIATION
                if method in {"POST", "PUT"}
                else OutcomeUncertainty.KNOWN
            )
            return self._failed(
                request,
                code="acquisition.http.timeout",
                category=FailureCategory.TIMEOUT,
                retryability=Retryability.RETRYABLE,
                summary="HTTP acquisition timed out after exhausting retry attempts.",
                uncertainty=uncertainty,
            )
        except HttpTransportErrorV2:
            uncertainty = (
                OutcomeUncertainty.REQUIRES_RECONCILIATION
                if method in {"POST", "PUT"}
                else OutcomeUncertainty.KNOWN
            )
            return self._failed(
                request,
                code="acquisition.http.transport",
                category=FailureCategory.EXTERNAL_PROVIDER,
                retryability=Retryability.RETRYABLE,
                summary="HTTP transport failed after exhausting retry attempts.",
                uncertainty=uncertainty,
            )
        finally:
            if owns_client:
                self._close_client(client)

        if response is None:
            raise AssertionError("HTTP acquisition ended without a terminal response.")
        final_url = response.url
        final_validation = self._validate_url(final_url)
        if final_validation is not None:
            return self._failed(
                request,
                code="acquisition.http.resolved_url_forbidden",
                category=FailureCategory.AUTHORIZATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="HTTP response resolved outside the configured network policy.",
            )
        persisted_url, redacted_query_count = _sanitize_url_for_persistence(final_url)
        media_type = _content_type(response.header("content-type"))
        checksum = hashlib.sha256(response.content).hexdigest()
        metadata = [
            ("requested_url", requested_url),
            ("resolved_url", persisted_url),
            ("method", method),
            ("status_code", str(response.status_code)),
            ("attempts", str(total_attempts)),
            ("redirect_count", str(redirect_count)),
        ]
        etag = response.header("etag")
        if etag is not None:
            metadata.append(("etag", etag))
        last_modified = response.header("last-modified")
        if last_modified is not None:
            metadata.append(("last_modified", last_modified))
        if redacted_query_count:
            metadata.append(("redacted_query_fields", str(redacted_query_count)))

        resource = ResourceReference(
            namespace="pyingestkit.resource.http",
            resource_id=hashlib.sha256(persisted_url.encode("utf-8")).hexdigest(),
            locator=persisted_url,
            media_type=media_type,
            format=_format_from_url(persisted_url),
            metadata=tuple(metadata),
        )
        diagnostic = Diagnostic(
            code="acquisition.http.succeeded",
            severity=DiagnosticSeverity.INFO,
            summary="HTTP source acquisition completed.",
            stage="acquire",
            source_context="http",
            details=(
                ("method", method),
                ("status_code", str(response.status_code)),
                ("attempts", str(total_attempts)),
                ("redirect_count", str(redirect_count)),
                ("size_bytes", str(len(response.content))),
                ("checksum_algorithm", "sha256"),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return AcquisitionResult(
            status=AcquisitionStatus.SUCCEEDED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            source_kind=SourceKind.HTTP,
            resource=resource,
            content=response.content,
            checksum_algorithm="sha256",
            checksum=checksum,
            size_bytes=len(response.content),
            media_type=media_type,
            source_metadata=tuple(metadata),
            diagnostics=(diagnostic,),
        )

    def _credential_headers(
        self,
        request: AcquisitionRequest,
        client: HttpClientV2,
    ) -> tuple[tuple[str, str], ...]:
        credential = request.source.credential
        if credential is None:
            return ()
        if self._oauth_manager is not None:
            return (self._oauth_manager.get_authorization_header(client),)
        if self._credential_resolver is None:
            raise ValueError(
                "HTTP Source declares a credential but no resolver or OAuth manager is configured."
            )
        return self._credential_resolver.headers_for(credential)

    def _client_for_acquisition(self) -> tuple[HttpClientV2 | None, bool]:
        if self._client is not None:
            return self._client, False
        if importlib.util.find_spec("httpx") is None:
            return None, False
        from pyingestkit.adapters.http._httpx import HttpxHttpClientV2

        return HttpxHttpClientV2(validator=self._validator), True

    @staticmethod
    def _close_client(client: HttpClientV2) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()

    def _send_with_retry(
        self,
        client: HttpClientV2,
        url: str,
        method: str,
        body: bytes,
        headers: tuple[tuple[str, str], ...],
        pinned_ip: str | None = None,
    ) -> tuple[HttpResponseV2, int]:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = client.send(
                    HttpRequestV2(
                        url=url,
                        method=method,
                        body=body,
                        headers=headers,
                        timeout_seconds=self._policy.timeout_seconds,
                        max_bytes=self._policy.max_bytes,
                        pinned_ip=pinned_ip,
                    )
                )
            except (HttpTimeoutErrorV2, HttpTransportErrorV2):
                if attempt >= self._policy.max_attempts:
                    raise
                self._sleep(self._backoff_delay(attempt, None))
                continue

            if (
                response.status_code in self._policy.retry_statuses
                and attempt < self._policy.max_attempts
            ):
                self._sleep(self._backoff_delay(attempt, response))
                continue
            return response, attempt

    def _backoff_delay(self, attempt: int, response: HttpResponseV2 | None) -> float:
        if response is not None:
            retry_after = response.header("retry-after")
            if retry_after is not None:
                try:
                    parsed = float(retry_after)
                except ValueError:
                    parsed = -1.0
                if parsed >= 0:
                    retry_cap: float = self._policy.max_retry_after_seconds
                    return parsed if parsed <= retry_cap else retry_cap
        base_delay = float(self._policy.retry_backoff_seconds) * (2 ** (attempt - 1))
        capped: float = min(base_delay, float(self._policy.max_backoff_seconds))
        if self._policy.retry_jitter:
            return float(random.uniform(0.0, capped))
        return float(capped)

    def _validate_url(
        self,
        url: str,
    ) -> tuple[str, FailureCategory, str] | None:
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError:
            return (
                "acquisition.http.invalid_url",
                FailureCategory.CONFIGURATION,
                "HTTP source URL is invalid.",
            )

        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return (
                "acquisition.http.invalid_url",
                FailureCategory.CONFIGURATION,
                "HTTP source URL must use http or https and include a host.",
            )
        if parsed.username is not None or parsed.password is not None:
            return (
                "acquisition.http.userinfo_forbidden",
                FailureCategory.AUTHENTICATION,
                "HTTP source URL must not embed user-info credentials.",
            )
        if scheme == "http" and not self._policy.allow_http:
            return (
                "acquisition.http.insecure_scheme",
                FailureCategory.AUTHORIZATION,
                "Plain HTTP is disabled by the configured acquisition policy.",
            )

        host = parsed.hostname.lower().rstrip(".")
        if host not in self._policy.normalized_hosts:
            return (
                "acquisition.http.host_forbidden",
                FailureCategory.AUTHORIZATION,
                "HTTP source host is outside the configured allow-list.",
            )

        default_port = 443 if scheme == "https" else 80
        if port is not None and port != default_port and port not in self._policy.allowed_ports:
            return (
                "acquisition.http.port_forbidden",
                FailureCategory.AUTHORIZATION,
                "HTTP source port is outside the configured allow-list.",
            )
        return None

    def _status_failure(
        self,
        request: AcquisitionRequest,
        response: HttpResponseV2,
    ) -> AcquisitionResult:
        status = response.status_code
        if status == 401:
            category = FailureCategory.AUTHENTICATION
            retryability = Retryability.NON_RETRYABLE
        elif status == 403:
            category = FailureCategory.AUTHORIZATION
            retryability = Retryability.NON_RETRYABLE
        elif status == 404:
            category = FailureCategory.NOT_FOUND
            retryability = Retryability.NON_RETRYABLE
        elif status == 429:
            category = FailureCategory.RATE_LIMITED
            retryability = Retryability.RETRYABLE
        elif status in self._policy.retry_statuses:
            category = FailureCategory.TRANSIENT
            retryability = Retryability.RETRYABLE
        else:
            category = FailureCategory.EXTERNAL_PROVIDER
            retryability = Retryability.NON_RETRYABLE

        return self._failed(
            request,
            code=f"acquisition.http.status_{status}",
            category=category,
            retryability=retryability,
            summary="HTTP source returned a non-success status.",
            details=(("status_code", str(status)),),
        )

    @staticmethod
    def _failed(
        request: AcquisitionRequest,
        *,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
        uncertainty: OutcomeUncertainty = OutcomeUncertainty.KNOWN,
        details: tuple[tuple[str, str], ...] = (),
    ) -> AcquisitionResult:
        failure = FailureEvidence(
            error_code=code,
            category=category,
            retryability=retryability,
            uncertainty=uncertainty,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
            source_component="http_source_connector",
            message_summary=summary,
            details=details,
        )
        return AcquisitionResult(
            status=AcquisitionStatus.FAILED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            source_kind=SourceKind.HTTP,
            failure=failure,
        )


def _content_type(value: str | None) -> str | None:
    if value is None:
        return None
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type or None


def _format_from_url(url: str) -> str | None:
    suffix = PurePosixPath(urlsplit(url).path).suffix.lower().lstrip(".")
    return suffix or None


def _sanitize_url_for_persistence(url: str) -> tuple[str, int]:
    parsed = urlsplit(url)
    safe_query: list[tuple[str, str]] = []
    redacted = 0
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            redacted += 1
            continue
        safe_query.append((key, value))
    sanitized = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path,
            urlencode(safe_query, doseq=True),
            "",
        )
    )
    return sanitized, redacted
