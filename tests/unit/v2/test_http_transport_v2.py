"""Unit tests for extended HTTP methods, payloads, jitter and network uncertainty."""

from __future__ import annotations

import pytest

from pyingestkit.adapters.http.source import HttpAccessPolicy, HttpSourceConnector
from pyingestkit.adapters.http.transport import (
    HttpRequestV2,
    HttpResponseV2,
    HttpTimeoutErrorV2,
)
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.runtime import CorrelationContext, OutcomeUncertainty
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source


class _RecordingClient:
    def __init__(self, response: HttpResponseV2 | Exception) -> None:
        self.response = response
        self.received_requests: list[HttpRequestV2] = []

    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        self.received_requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _request_with_options(
    url: str = "https://api.example.test/search",
    method: str | None = None,
    payload: str | None = None,
) -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    metadata: list[tuple[str, str]] = []
    if method is not None:
        metadata.append(("http_method", method))
    if payload is not None:
        metadata.append(("http_payload", payload))

    source = Source.http(
        url=url,
        metadata=tuple(metadata),
    )
    return AcquisitionRequest(
        source=source,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )


def test_http_request_v2_method_and_body_validation() -> None:
    # Nominal methods
    req_get = HttpRequestV2(url="https://api.example.test/items", method="GET")
    assert req_get.method == "GET"
    assert req_get.body == b""

    req_post = HttpRequestV2(
        url="https://api.example.test/items",
        method="POST",
        body=b'{"filter": "active"}',
        pinned_ip="93.184.216.34",
    )
    assert req_post.method == "POST"
    assert req_post.body == b'{"filter": "active"}'
    assert req_post.pinned_ip == "93.184.216.34"

    # Rejection of invalid methods
    with pytest.raises(ValueError, match="must be one of"):
        HttpRequestV2(url="https://api.example.test/items", method="DELETE")

    # Rejection of non-bytes body
    with pytest.raises(TypeError, match="body must be bytes"):
        HttpRequestV2(
            url="https://api.example.test/items",
            method="POST",
            body="string-payload",  # type: ignore[arg-type]
        )


def test_connector_executes_post_with_payload_from_metadata() -> None:
    client = _RecordingClient(
        HttpResponseV2(200, "https://api.example.test/search", (), b'{"count": 42}')
    )
    policy = HttpAccessPolicy(allowed_hosts=("api.example.test",))
    connector = HttpSourceConnector(policy=policy, client=client)

    request = _request_with_options(
        url="https://api.example.test/search",
        method="POST",
        payload='{"status": "CONFIRMED"}',
    )
    result = connector.acquire(request)

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.content == b'{"count": 42}'
    assert len(client.received_requests) == 1
    sent_request = client.received_requests[0]
    assert sent_request.method == "POST"
    assert sent_request.body == b'{"status": "CONFIRMED"}'


def test_connector_rejects_unsupported_http_method() -> None:
    client = _RecordingClient(HttpResponseV2(200, "https://api.example.test/items", (), b""))
    policy = HttpAccessPolicy(allowed_hosts=("api.example.test",))
    connector = HttpSourceConnector(policy=policy, client=client)

    request = _request_with_options(
        url="https://api.example.test/items",
        method="TRACE",
    )
    result = connector.acquire(request)

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.invalid_method"
    assert len(client.received_requests) == 0


def test_connector_network_uncertainty_on_post_timeout() -> None:
    # Simulate a network timeout during a POST request
    client = _RecordingClient(HttpTimeoutErrorV2("Timeout during POST"))
    policy = HttpAccessPolicy(
        allowed_hosts=("api.example.test",),
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )
    connector = HttpSourceConnector(policy=policy, client=client)

    request = _request_with_options(
        url="https://api.example.test/orders",
        method="POST",
        payload='{"order_id": 123}',
    )
    result = connector.acquire(request)

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.timeout"
    # POST mutation uncertainty must require reconciliation
    assert result.failure.uncertainty is OutcomeUncertainty.REQUIRES_RECONCILIATION


def test_connector_network_uncertainty_on_get_timeout() -> None:
    # Simulate a network timeout during a GET request (idempotent read)
    client = _RecordingClient(HttpTimeoutErrorV2("Timeout during GET"))
    policy = HttpAccessPolicy(
        allowed_hosts=("api.example.test",),
        max_attempts=1,
        retry_backoff_seconds=0.0,
    )
    connector = HttpSourceConnector(policy=policy, client=client)

    request = _request_with_options(
        url="https://api.example.test/orders/123",
        method="GET",
    )
    result = connector.acquire(request)

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.http.timeout"
    # GET idempotent read uncertainty must be KNOWN
    assert result.failure.uncertainty is OutcomeUncertainty.KNOWN


def test_jitter_backoff_calculation() -> None:
    policy_jitter = HttpAccessPolicy(
        allowed_hosts=("api.example.test",),
        retry_backoff_seconds=1.0,
        max_backoff_seconds=10.0,
        retry_jitter=True,
    )
    connector_jitter = HttpSourceConnector(policy=policy_jitter)

    # Delay with jitter should be bounded in [0, 1.0] for attempt 1
    delay1 = connector_jitter._backoff_delay(1, None)
    assert 0.0 <= delay1 <= 1.0

    # Delay without jitter should be deterministic
    policy_deterministic = HttpAccessPolicy(
        allowed_hosts=("api.example.test",),
        retry_backoff_seconds=0.5,
        max_backoff_seconds=10.0,
        retry_jitter=False,
    )
    connector_deterministic = HttpSourceConnector(policy=policy_deterministic)
    assert connector_deterministic._backoff_delay(1, None) == 0.5
    assert connector_deterministic._backoff_delay(2, None) == 1.0
    assert connector_deterministic._backoff_delay(3, None) == 2.0
