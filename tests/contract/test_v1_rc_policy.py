from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "release_candidate_v1.json"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_rc1_contract_is_versioned_and_anchored_to_b2() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["milestone"] == "V1.0.0-rc1"
    assert contract["baseline"]["b2_merge_sha"] == (
        "a29be350498aae1c2002c280aead7e4d1f02cff9"
    )


def test_rc1_versions_are_candidate_versions_not_stable() -> None:
    contract = _contract()
    versions = contract["versions"]
    assert versions["framework"] == "1.0.0rc1"
    assert versions["demo_package"] == "1.0.0rc1"
    assert versions["stable_target"] == "1.0.0"
    assert contract["scope"]["creates_stable_tag"] is False


def test_rc1_does_not_expand_product_scope() -> None:
    scope = _contract()["scope"]
    assert scope["introduces_new_ingestion_provider"] is False
    assert scope["introduces_orchestration_platform"] is False


def test_rc1_keeps_v060_as_explicit_upgrade_baseline() -> None:
    assert _contract()["baseline"]["upgrade_from"] == "0.6.0"


def test_rc1_machine_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_v1_rc.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "V1.0.0-rc1" in result.stdout


