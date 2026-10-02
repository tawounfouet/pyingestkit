from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_ARTIFACT_VALUES,
)
from pyingestkit.domain.artifacts import (
    ArtifactKind,
    ArtifactPutStatus,
    RawArtifactEvidence,
)
from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_artifacts.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_lot04_phase_and_completed_lots_are_recorded() -> None:
    assert "LOT-04" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-04") < V2_COMPLETED_LOTS.index("LOT-05")
    assert V2_API_PHASE.startswith(V2_COMPLETED_LOTS[-1])
    assert "FileArtifactStore" in V2_IMPLEMENTED_ARTIFACT_VALUES


def test_artifact_kind_and_status_contracts_match_fixture() -> None:
    payload = _fixture()

    assert [value.value for value in ArtifactKind] == payload["artifact_kinds"]
    assert [value.value for value in ArtifactPutStatus] == payload["put_statuses"]


def test_artifact_store_protocol_surface_matches_fixture() -> None:
    payload = _fixture()
    store_methods = sorted(
        name for name in ("put", "open", "exists") if hasattr(ArtifactStore, name)
    )
    reader_methods = sorted(name for name in ("reference", "read") if hasattr(ArtifactReader, name))

    assert store_methods == sorted(payload["store_methods"])
    assert reader_methods == sorted(payload["reader_methods"])


def test_raw_evidence_fields_match_fixture() -> None:
    payload = _fixture()

    assert [field.name for field in fields(RawArtifactEvidence)] == payload["raw_evidence_fields"]
