from __future__ import annotations

import pyingestkit.sources.v2 as sources_v2
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_HTTP_VALUES,
)
from pyingestkit.sources.http.v2 import (
    HttpAccessPolicy,
    HttpClientV2,
    HttpCredentialResolverV2,
    HttpRequestV2,
    HttpResponseTooLargeErrorV2,
    HttpResponseV2,
    HttpSourceConnector,
    HttpTimeoutErrorV2,
    HttpTransportErrorV2,
)

_EXPECTED = (
    "HttpAccessPolicy",
    "HttpClientV2",
    "HttpCredentialResolverV2",
    "HttpRequestV2",
    "HttpResponseTooLargeErrorV2",
    "HttpResponseV2",
    "HttpSourceConnector",
    "HttpTimeoutErrorV2",
    "HttpTransportErrorV2",
)


def test_lot13_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-13" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-13") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot13_http_values_are_recorded_and_importable() -> None:
    assert V2_IMPLEMENTED_HTTP_VALUES == _EXPECTED
    values = (
        HttpAccessPolicy,
        HttpClientV2,
        HttpCredentialResolverV2,
        HttpRequestV2,
        HttpResponseTooLargeErrorV2,
        HttpResponseV2,
        HttpSourceConnector,
        HttpTimeoutErrorV2,
        HttpTransportErrorV2,
    )
    assert tuple(value.__name__ for value in values) == _EXPECTED


def test_lot13_http_values_are_available_from_cumulative_source_v2_namespace() -> None:
    for name in _EXPECTED:
        assert hasattr(sources_v2, name)
