from __future__ import annotations

from dataclasses import dataclass

from pyingestkit.adapters.http import (
    HttpAccessPolicy,
    HttpCredentialResolverV2,
    HttpRequestV2,
    HttpResponseV2,
    HttpSourceConnector,
    HttpTimeoutErrorV2,
)
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionStatus,
)
from pyingestkit.domain.resources import CredentialReference
from pyingestkit.domain.runtime import CorrelationContext, FailureCategory, Retryability
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source


@dataclass
class _SequenceClient:
    sequence: list[HttpResponseV2 | Exception]

    def __post_init__(self) -> None:
        self.requests: list[HttpRequestV2] = []

    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        self.requests.append(request)
        item = self.sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _request(
    *,
    url: str = "https://api.example.test/data.csv?page=1",
    credential: CredentialReference | None = None,
) -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(run_id))
    return AcquisitionRequest(
        source=Source.http(url=url, credential=credential),
        ingestion_run_id=run_id,
        correlation=correlation,
    )


def _policy(**overrides: object) -> HttpAccessPolicy:
    values: dict[str, object] = {
        "allowed_hosts": ("api.example.test",),
        "retry_backoff_seconds": 0.0,
    }
    values.update(overrides)
    return HttpAccessPolicy(**values)  # type: ignore[arg-type]


def test_http_acquisition_keeps_credentials_and_sensitive_redirect_query_out_of_evidence() -> None:
    credential = CredentialReference("demo-http", provider="test")
    client = _SequenceClient(
        [
            HttpResponseV2(
                302,
                "https://api.example.test/data.csv?page=1",
                (
                    (
                        "Location",
                        "https://api.example.test/final.csv?token=redirect-secret&page=2",
                    ),
                ),
                b"",
            ),
            HttpResponseV2(
                200,
                "https://api.example.test/final.csv?token=redirect-secret&page=2",
                (
                    ("Content-Type", "text/csv; charset=utf-8"),
                    ("ETag", '"v7"'),
                    ("Last-Modified", "Wed, 02 Sep 2026 10:00:00 GMT"),
                    ("Set-Cookie", "session=response-cookie-secret"),
                    ("X-Auth-Token", "response-token-secret"),
                ),
                b"id,name\n1,Ada\n",
            ),
        ]
    )
    connector = HttpSourceConnector(
        policy=_policy(),
        client=client,
        credential_resolver=HttpCredentialResolverV2(
            lambda ref: {
                "Authorization": f"Bearer auth-secret-{ref.credential_id}",
                "Cookie": "sid=cookie-secret",
            }
        ),
    )

    result = connector.acquire(_request(credential=credential))

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.resource is not None
    assert result.resource.locator == "https://api.example.test/final.csv?page=2"
    assert result.media_type == "text/csv"
    assert result.size_bytes == len(b"id,name\n1,Ada\n")
    assert len(client.requests) == 2
    assert dict(client.requests[0].headers)["Authorization"].startswith("Bearer auth-secret")
    assert "redirect-secret" in client.requests[1].url

    persisted = "\n".join(
        [
            result.resource.locator or "",
            repr(result.resource.metadata),
            repr(result.source_metadata),
            repr(result.diagnostics),
        ]
    )
    for secret in (
        "auth-secret",
        "cookie-secret",
        "redirect-secret",
        "response-cookie-secret",
        "response-token-secret",
    ):
        assert secret not in persisted
    assert "Set-Cookie" not in persisted
    assert "X-Auth-Token" not in persisted


def test_http_acquisition_blocks_redirect_to_unapproved_host_before_second_request() -> None:
    client = _SequenceClient(
        [
            HttpResponseV2(
                302,
                "https://api.example.test/data.csv",
                (("Location", "https://evil.example.test/steal.csv"),),
                b"",
            )
        ]
    )
    connector = HttpSourceConnector(policy=_policy(), client=client)

    result = connector.acquire(_request(url="https://api.example.test/data.csv"))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.redirect_forbidden"
    assert result.failure.category is FailureCategory.AUTHORIZATION
    assert len(client.requests) == 1


def test_http_acquisition_retries_transient_status_then_succeeds() -> None:
    sleeps: list[float] = []
    client = _SequenceClient(
        [
            HttpResponseV2(
                503,
                "https://api.example.test/data.csv",
                (("Retry-After", "0"),),
                b"temporarily unavailable",
            ),
            HttpResponseV2(
                200,
                "https://api.example.test/data.csv",
                (("Content-Type", "text/csv"),),
                b"id\n1\n",
            ),
        ]
    )
    connector = HttpSourceConnector(
        policy=_policy(max_attempts=2),
        client=client,
        sleep=sleeps.append,
    )

    result = connector.acquire(_request(url="https://api.example.test/data.csv"))

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert len(client.requests) == 2
    assert sleeps == [0.0]
    assert ("attempts", "2") in result.source_metadata


def test_http_timeout_is_structured_after_bounded_retries() -> None:
    sleeps: list[float] = []
    client = _SequenceClient(
        [
            HttpTimeoutErrorV2("timeout-1"),
            HttpTimeoutErrorV2("timeout-2"),
        ]
    )
    connector = HttpSourceConnector(
        policy=_policy(max_attempts=2),
        client=client,
        sleep=sleeps.append,
    )

    result = connector.acquire(_request())

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.timeout"
    assert result.failure.category is FailureCategory.TIMEOUT
    assert result.failure.retryability is Retryability.RETRYABLE
    assert len(client.requests) == 2
    assert sleeps == [0.0]


def test_http_policy_rejects_plain_http_by_default() -> None:
    client = _SequenceClient([])
    connector = HttpSourceConnector(policy=_policy(), client=client)

    result = connector.acquire(_request(url="http://api.example.test/data.csv"))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.insecure_scheme"
    assert client.requests == []
