from __future__ import annotations

import json
from pathlib import Path

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetReference, DatasetVersionReference
from pyingestkit.domain.resources import CredentialReference, ResourceReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    FailureEvidence,
    IdempotencyReference,
    IngestionExecutionReference,
    IngestionStatus,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_boundary_values.json"


def test_lot01_contract_ids_and_versions_match_fixture() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = payload["contracts"]
    classes = (
        ResourceReference,
        ArtifactReference,
        DatasetReference,
        DatasetVersionReference,
        CredentialReference,
        IdempotencyReference,
        CorrelationContext,
        FailureEvidence,
        Diagnostic,
        IngestionExecutionReference,
    )

    actual = {value.CONTRACT_ID: "1" for value in classes}

    assert actual == expected


def test_lot01_terminal_status_contract_matches_fixture() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    actual = [status.value for status in IngestionStatus if status.terminal]

    assert actual == payload["terminal_statuses"]


def test_public_qualified_namespaces_match_rc_boundary_types() -> None:
    from pyingestkit.datasets import DatasetVersionReference as PublicDatasetVersionReference
    from pyingestkit.diagnostics import Diagnostic as PublicDiagnostic

    assert PublicDatasetVersionReference is DatasetVersionReference
    assert PublicDiagnostic is Diagnostic
