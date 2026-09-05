from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v1.json"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_stable_contract_is_anchored_to_qualified_rc1() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["milestone"] == "V1.0.0"
    assert contract["baseline"]["rc1_merge_sha"] == ("e98a12cc3bbfb634d2fd2257f43049fa1e0333dd")
    assert contract["baseline"]["upgrade_from"] == "0.6.0"


def test_stable_versions_and_tag_policy_are_final() -> None:
    contract = _contract()
    assert contract["versions"]["framework"] == "1.0.0"
    assert contract["versions"]["demo_package"] == "1.0.0"
    assert contract["versions"]["release_candidate"] == "1.0.0rc1"
    assert contract["release"]["tag"] == "v1.0.0"
    assert contract["release"]["tag_kind"] == "annotated"
    assert contract["release"]["immutable"] is True
    assert "post-merge" in contract["release"]["creation_phase"]


def test_stable_promotion_does_not_expand_product_or_schema_scope() -> None:
    scope = _contract()["scope"]
    assert scope["introduces_new_ingestion_provider"] is False
    assert scope["introduces_orchestration_platform"] is False
    assert scope["changes_persisted_schema_versions"] is False


def test_stable_public_api_promotion_preserves_experimentals() -> None:
    public_api = _contract()["public_api"]
    assert public_api["promotion_from"] == "PUBLIC_STABLE_CANDIDATE"
    assert public_api["promotion_to"] == "PUBLIC_STABLE"
    assert public_api["experimental_remains_experimental"] is True


def test_stable_machine_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_v1_stable.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "V1.0.0 stable release contract" in result.stdout
