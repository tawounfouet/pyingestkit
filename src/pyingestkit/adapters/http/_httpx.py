"""HTTPX-backed implementation of the V2 HTTP transport port."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx

from pyingestkit.adapters.http.transport import (
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)


class HttpxHttpClientV2:
    """Synchronous HTTPX adapter with bounded response-body reads."""

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self._owns_client = client is None

    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        try:
            with self._client.stream(
                "GET",
                request.url,
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
        except httpx.TimeoutException as exc:
            raise HttpTimeoutErrorV2("HTTP acquisition timed out.") from exc
        except httpx.HTTPError as exc:
            raise HttpTransportErrorV2(
                f"HTTP transport failed with {type(exc).__name__}."
            ) from exc

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
