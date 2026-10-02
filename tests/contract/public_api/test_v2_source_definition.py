from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pyingestkit
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_IMPLEMENTED_AUTHORING_VALUES,
    V2_PROVISIONAL_ROOT_EXPORTS,
)
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.sources import SourceKind

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_ingestion_definition.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_lot02_phase_and_authoring_values_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-02_SOURCE_DEFINITION"
    assert "IngestionDefinition" in V2_IMPLEMENTED_AUTHORING_VALUES
    assert "Source" in V2_IMPLEMENTED_AUTHORING_VALUES


def test_lot02_provisional_root_imports_match_fixture() -> None:
    payload = _fixture()

    assert list(V2_PROVISIONAL_ROOT_EXPORTS) == payload["provisional_root_imports"]
    for name in V2_PROVISIONAL_ROOT_EXPORTS:
        assert hasattr(pyingestkit, name)


def test_lot02_definition_fields_match_contract_fixture() -> None:
    payload = _fixture()
    actual = [field.name for field in fields(IngestionDefinition)]

    assert actual == payload["definition_fields"]


def test_lot02_source_kinds_match_contract_fixture() -> None:
    payload = _fixture()

    assert [kind.value for kind in SourceKind] == payload["source_kinds"]
