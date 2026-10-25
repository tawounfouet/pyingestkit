"""HTTPX-backed implementation of the V2 HTTP transport port with SSRF hardening."""

from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType
from typing import Any, Self

import httpcore
import httpx

from pyingestkit.adapters.http._ssrf import AntiSsrfValidator, SsrfSecurityError
from pyingestkit.adapters.http.transport import (
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)


class SsrfSafeNetworkBackend(httpcore.NetworkBackend):
    """NetworkBackend that validates destinations against SSRF rules before TCP connect."""

    def __init__(self, validator: AntiSsrfValidator) -> None:
        self._validator = validator
        self._real_backend = httpcore.NetworkBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.NetworkStream:
        resolved_ips = self._validator.resolve_and_validate(host, port)
        target_ip = resolved_ips[0]
        return self._real_backend.connect_tcp(
            target_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.NetworkStream:
        raise SsrfSecurityError("UNIX domain socket connections are forbidden by SSRF policy.")

    def sleep(self, seconds: float) -> None:
        self._real_backend.sleep(seconds)


def create_ssrf_safe_transport(
    validator: AntiSsrfValidator | None = None,
) -> httpx.HTTPTransport:
    """Create an HTTPX transport with SSRF protection and DNS rebinding immunity."""
    effective_validator = validator or AntiSsrfValidator()
    backend = SsrfSafeNetworkBackend(effective_validator)
    pool = httpcore.ConnectionPool(network_backend=backend)
    transport = httpx.HTTPTransport()
    transport._pool = pool
    return transport


class HttpxHttpClientV2:
    """Synchronous HTTPX adapter with bounded response-body reads and SSRF hardening."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        validator: AntiSsrfValidator | None = None,
    ) -> None:
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            transport = create_ssrf_safe_transport(validator)
            self._client = httpx.Client(transport=transport)
            self._owns_client = True

    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        try:
            with self._client.stream(
                request.method,
                request.url,
                content=request.body if request.body else None,
                headers=dict(request.headers),
                timeout=request.timeout_seconds,
                follow_redirects=False,
            ) as response:
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError:
                        declared_size = None
                    if declared_size is not None and declared_size > request.max_bytes:
                        raise HttpResponseTooLargeErrorV2(
                            "HTTP response Content-Length exceeds the configured acquisition limit."
                        )

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > request.max_bytes:
                        raise HttpResponseTooLargeErrorV2(
                            "HTTP response body exceeds the configured acquisition limit."
                        )

                return HttpResponseV2(
                    status_code=response.status_code,
                    url=str(response.url),
                    headers=tuple((key, value) for key, value in response.headers.items()),
                    content=bytes(body),
                )
        except HttpResponseTooLargeErrorV2:
            raise
        except SsrfSecurityError:
            raise
        except httpx.TimeoutException as exc:
            raise HttpTimeoutErrorV2("HTTP acquisition timed out.") from exc
        except httpx.HTTPError as exc:
            raise HttpTransportErrorV2(f"HTTP transport failed with {type(exc).__name__}.") from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
