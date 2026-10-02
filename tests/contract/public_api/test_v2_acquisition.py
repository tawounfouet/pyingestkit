from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from pyingestkit._api_v2 import (
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_ACQUISITION_VALUES,
)
from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
)
from pyingestkit.ports.sources import SourceConnectorCapability

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_acquisition.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_lot03_is_recorded_cumulatively() -> None:
    assert "LOT-03" in V2_COMPLETED_LOTS
    assert "AcquisitionRequest" in V2_IMPLEMENTED_ACQUISITION_VALUES
    assert "FileSourceConnector" in V2_IMPLEMENTED_ACQUISITION_VALUES


def test_lot03_request_and_result_fields_match_fixture() -> None:
    payload = _fixture()

    assert [field.name for field in fields(AcquisitionRequest)] == payload[
        "request_fields"
    ]
    assert [field.name for field in fields(AcquisitionResult)] == payload[
        "result_fields"
    ]


def test_lot03_status_and_file_connector_contract_match_fixture(
    tmp_path: Path,
) -> None:
    payload = _fixture()
    connector = FileSourceConnector(
        policy=FileAccessPolicy(allowed_roots=(tmp_path,))
    )

    assert [status.value for status in AcquisitionStatus] == payload["statuses"]
    assert connector.descriptor.id == payload["connector_id"]
    assert connector.descriptor.connector_version == payload[
        "connector_version"
    ]
    assert [
        capability.value for capability in connector.descriptor.capabilities
    ] == payload["capabilities"]
    assert connector.descriptor.capabilities == (
        SourceConnectorCapability.ACQUIRE,
    )
