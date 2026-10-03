from __future__ import annotations

import json
from pathlib import Path

import pyingestkit
import pyingestkit.governance as governance
from pyingestkit.ports.governance import (
    ConditionalDatasetPublisher,
    DatasetVersionGarbageCollector,
    PublicationLedger,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "governance_v2_1_alpha1.json"
)


def _method_names(protocol: type[object]) -> set[str]:
    return {
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def test_governance_namespace_matches_lot23_fixture() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert tuple(governance.__all__) == tuple(fixture["namespace_exports"])


def test_lot23_does_not_widen_frozen_package_root() -> None:
    stable = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "stable_release_v2.json"
        ).read_text(encoding="utf-8")
    )
    assert tuple(pyingestkit.__all__) == tuple(stable["root_exports"])
    assert "PublicationLedger" not in pyingestkit.__all__


def test_governance_protocol_signatures_match_lot23_fixture() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    protocols = {
        "pyingestkit.ports.governance.PublicationLedger": PublicationLedger,
        "pyingestkit.ports.governance.ConditionalDatasetPublisher": ConditionalDatasetPublisher,
        "pyingestkit.ports.governance.DatasetVersionGarbageCollector": (
            DatasetVersionGarbageCollector
        ),
    }
    for qualified_name, protocol in protocols.items():
        assert _method_names(protocol) == set(fixture["protocols"][qualified_name])
