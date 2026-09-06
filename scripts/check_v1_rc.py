from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "release_candidate_v1.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def main() -> None:
    contract = _contract()
    versions = contract["versions"]

    if contract["milestone"] != "V1.0.0-rc1":
        raise SystemExit("RC1 historical contract milestone drift")
    if versions["framework"] != "1.0.0rc1" or versions["demo_package"] != "1.0.0rc1":
        raise SystemExit("RC1 historical package versions drifted")
    if versions["stable_target"] != "1.0.0":
        raise SystemExit("RC1 stable target drifted")
    if contract["baseline"]["upgrade_from"] != "0.6.0":
        raise SystemExit("RC1 historical upgrade baseline must remain V0.6.0")
    if contract["scope"]["creates_stable_tag"] is not False:
        raise SystemExit("RC1 governance must remain explicitly pre-stable")
    if contract["scope"]["introduces_new_ingestion_provider"] is not False:
        raise SystemExit("RC1 historical scope unexpectedly introduces a provider")
    if contract["scope"]["introduces_orchestration_platform"] is not False:
        raise SystemExit("RC1 historical scope unexpectedly introduces orchestration")

    for relative in contract["required_docs"] + contract["required_scripts"]:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Missing RC1 historical evidence file: {relative}")

    release_notes = ROOT / "docs" / "releases" / "v1.0.0rc1.md"
    release_text = release_notes.read_text(encoding="utf-8")
    if "1.0.0rc1" not in release_text or "not stable" not in release_text.lower():
        raise SystemExit("RC1 release notes no longer identify the candidate state")

    print(
        "OK: historical V1.0.0-rc1 release contract evidence remains intact "
        "(candidate=1.0.0rc1, stable_target=1.0.0, upgrade_from=0.6.0)"
    )


if __name__ == "__main__":
    main()
