from __future__ import annotations

from dataclasses import dataclass

from pyingestkit import RunContext
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.retry import RetryPolicy
from pyingestkit.sources.http import HttpRequest, HttpResponse, HttpSource


@dataclass(slots=True)
class FixtureSequenceClient:
    """Deterministic offline HTTP client used only by the demo job pack."""

    content: bytes
    content_type: str
    attempts: int = 0

    def send(self, request: HttpRequest) -> HttpResponse:
        self.attempts += 1
        if self.attempts == 1:
            return HttpResponse(
                503,
                headers={"Retry-After": "0"},
                url=request.effective_url,
                elapsed_seconds=0.001,
            )
        return HttpResponse(
            200,
            headers={
                "Content-Type": self.content_type,
                "ETag": '"demo-fixture-v1"',
                "Last-Modified": "Thu, 03 Sep 2026 20:00:00 GMT",
            },
            content=self.content,
            url=request.effective_url,
            elapsed_seconds=0.001,
        )


def reference_http_source(
    context: RunContext,
    *,
    fixture_content: bytes,
    content_type: str,
    artifact_name: str,
) -> HttpSource:
    """Build the reference source without allowing tests to touch the network."""
    runtime_url = context.parameter("url")
    if context.fixture_mode:
        url = str(runtime_url or f"https://fixtures.pyingestkit.invalid/{artifact_name}")
        client = FixtureSequenceClient(fixture_content, content_type)
        retry = RetryPolicy(
            max_attempts=2,
            initial_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter=False,
        )
        return HttpSource(url, client=client, retry=retry, artifact_name=artifact_name)
    if runtime_url in (None, ""):
        raise ConfigurationError(
            "HTTP demo jobs require runtime parameter 'url' outside fixture mode. "
            "Use --fixture for the fully offline reference slice."
        )
    return HttpSource(str(runtime_url), artifact_name=artifact_name)
