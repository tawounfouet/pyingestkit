from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_FORBIDDEN_LEGACY_ROOT_EXPORTS,
    V2_TARGET_ROOT_EXPORTS,
)


def test_target_api_contract_has_no_legacy_aliases() -> None:
    assert set(V2_TARGET_ROOT_EXPORTS).isdisjoint(V2_FORBIDDEN_LEGACY_ROOT_EXPORTS)


def test_target_api_uses_domain_qualified_runtime_names() -> None:
    assert "IngestionRun" in V2_TARGET_ROOT_EXPORTS
    assert "IngestionResult" in V2_TARGET_ROOT_EXPORTS
    assert "Run" not in V2_TARGET_ROOT_EXPORTS
    assert "Result" not in V2_TARGET_ROOT_EXPORTS
