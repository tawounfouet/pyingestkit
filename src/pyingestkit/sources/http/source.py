from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Self
from urllib.parse import unquote, urlsplit

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.replay.resolver import materialize_replayed_raw
from pyingestkit.retry import RetryAttempt, RetryPolicy, parse_retry_after
from pyingestkit.sources.base import Source

from .client import HttpClient, HttpxClient
from .exceptions import HttpStatusError, HttpTimeoutError, HttpTransportError
from .request import HttpRequest, QueryValue
from .response import HttpResponse

logger = logging.getLogger(__name__)


def _default_artifact_name(response: HttpResponse) -> str:
    path = urlsplit(response.url).path
    name = unquote(PurePosixPath(path).name)
    return name or "response.bin"


def _artifact_name_from_url(url: str) -> str:
    path = urlsplit(url).path
    name = unquote(PurePosixPath(path).name)
    return name or "response.bin"


class HttpSource(Source):
    """Reliable HTTP acquisition source producing immutable RAW artifacts.

    `fetch_response()` remains available for transport-level callers and tests.
    `fetch(context)` is the Alpha 2 ingestion surface: successful response bytes
    are written once to ArtifactStore with a SHA-256 digest and a deliberately
    narrow, secret-free provenance allow-list.
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
        artifact_name: str | None = None,
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
        self.artifact_name = artifact_name

    @classmethod
    def from_request(
        cls,
        request: HttpRequest,
        *,
        retry: RetryPolicy | None = None,
        client: HttpClient | None = None,
        artifact_name: str | None = None,
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
            artifact_name=artifact_name,
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

    def fetch(self, context: RunContext) -> RawArtifact:
        if context.replay is not None:
            name = self.artifact_name or _artifact_name_from_url(self.request.safe_url)
            origin = context.replay.resolve_raw(name, self.request.safe_url)
            return materialize_replayed_raw(context, origin, name=name)
        response = self.fetch_response()
        name = self.artifact_name or _default_artifact_name(response)
        artifact = context.artifact_store.write_raw(
            context.job_id,
            context.run_id,
            name=name,
            data=response.content,
            source_uri=self.request.safe_url,
            content_type=response.content_type,
            resolved_url=response.safe_url or self.request.safe_url,
            status_code=response.status_code,
            etag=response.etag,
            last_modified=response.last_modified,
        )
        logger.debug(
            "HTTP RAW artifact captured path=%s bytes=%d sha256=%s status=%d",
            artifact.path,
            artifact.size_bytes,
            artifact.sha256,
            response.status_code,
        )
        return artifact
