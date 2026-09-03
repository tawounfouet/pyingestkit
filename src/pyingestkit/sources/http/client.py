from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

import httpx

from .exceptions import HttpTimeoutError, HttpTransportError
from .request import HttpRequest
from .response import HttpResponse


class HttpClient(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse: ...


class HttpxClient:
    """Default synchronous HTTP adapter.

    HTTPX is deliberately contained behind the HttpClient protocol so job code
    and the rest of PyIngestKit do not depend on httpx.Response.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if client is not None and transport is not None:
            raise ValueError("Provide either client or transport, not both")
        self._client = client or httpx.Client(transport=transport)
        self._owns_client = client is None

    def send(self, request: HttpRequest) -> HttpResponse:
        try:
            response = self._client.request(
                request.method,
                request.effective_url,
                headers=dict(request.headers),
                timeout=request.timeout_seconds,
                follow_redirects=request.follow_redirects,
            )
        except httpx.TimeoutException as exc:
            raise HttpTimeoutError(request.method, request.url, request.timeout_seconds) from exc
        except httpx.HTTPError as exc:
            raise HttpTransportError(request.method, request.url, exc.__class__.__name__) from exc

        elapsed_seconds: float | None
        try:
            elapsed_seconds = response.elapsed.total_seconds()
        except RuntimeError:
            elapsed_seconds = None
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            url=str(response.url),
            elapsed_seconds=elapsed_seconds,
        )

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
