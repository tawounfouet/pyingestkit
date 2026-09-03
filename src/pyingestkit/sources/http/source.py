from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Self

from pyingestkit.retry import RetryAttempt, RetryPolicy, parse_retry_after

from .client import HttpClient, HttpxClient
from .exceptions import HttpStatusError, HttpTimeoutError, HttpTransportError
from .request import HttpRequest, QueryValue
from .response import HttpResponse

logger = logging.getLogger(__name__)


class HttpSource:
    """HTTP transport acquisition primitive for V0.2 Alpha 1.

    Alpha 1 intentionally stops at HttpResponse. Alpha 2 will add the
    ArtifactStore/RawArtifact bridge while preserving `fetch_response()`.
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, QueryValue] | None = None,
        timeout_seconds: float = 30.0,
        follow_redirects: bool = True,
        retry: RetryPolicy | None = None,
        client: HttpClient | None = None,
    ) -> None:
        self.request = HttpRequest(
            method=method,
            url=url,
            headers=headers or {},
            params=params or {},
            timeout_seconds=timeout_seconds,
            follow_redirects=follow_redirects,
        )
        self.retry = retry or RetryPolicy()
        self._client = client

    @classmethod
    def from_request(
        cls,
        request: HttpRequest,
        *,
        retry: RetryPolicy | None = None,
        client: HttpClient | None = None,
    ) -> Self:
        return cls(
            request.url,
            method=request.method,
            headers=request.headers,
            params=request.params,
            timeout_seconds=request.timeout_seconds,
            follow_redirects=request.follow_redirects,
            retry=retry,
            client=client,
        )

    def fetch_response(self) -> HttpResponse:
        client = self._client or HttpxClient()
        owns_client = self._client is None
        attempts = 0

        def send_once() -> HttpResponse:
            nonlocal attempts
            attempts += 1
            logger.debug(
                "HTTP request started method=%s url=%s attempt=%d",
                self.request.method,
                self.request.safe_url,
                attempts,
            )
            response = client.send(self.request)
            if response.status_code >= 400:
                raise HttpStatusError(
                    self.request.method,
                    response.url or self.request.url,
                    response.status_code,
                    headers=response.headers,
                )
            return response

        def should_retry(exception: BaseException) -> bool:
            if not self.retry.is_method_retryable(self.request.method):
                return False
            if isinstance(exception, (HttpTimeoutError, HttpTransportError)):
                return True
            if isinstance(exception, HttpStatusError):
                return self.retry.is_status_retryable(exception.status_code)
            return False

        def retry_after(exception: BaseException) -> float | None:
            if not isinstance(exception, HttpStatusError):
                return None
            value = exception.headers.get("retry-after") or exception.headers.get("Retry-After")
            return parse_retry_after(value)

        def on_retry(attempt: RetryAttempt) -> None:
            logger.warning(
                "HTTP attempt failed retry=%d/%d next_attempt=%d delay=%.3fs error=%s",
                attempt.attempt_number,
                self.retry.max_attempts,
                attempt.next_attempt_number,
                attempt.delay_seconds,
                str(attempt.exception),
            )

        try:
            response = self.retry.execute(
                send_once,
                should_retry=should_retry,
                retry_after=retry_after,
                on_retry=on_retry,
            )
        finally:
            if owns_client and isinstance(client, HttpxClient):
                client.close()

        logger.info(
            "HTTP fetch succeeded status=%d bytes=%d attempts=%d url=%s",
            response.status_code,
            response.content_length,
            attempts,
            response.safe_url,
        )
        return response
