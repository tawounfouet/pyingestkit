from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyingestkit

MANIFEST_PATH = ROOT / "tests" / "contract" / "fixtures" / "public_api_v1.json"
EXPECTED_PACKAGE_VERSION = "1.0.0rc1"


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main() -> None:
    manifest = _manifest()
    for module_name, contract in manifest["modules"].items():
        module = importlib.import_module(module_name)
        expected = set(contract["exports"])
        actual = set(module.__all__)
        if actual != expected:
            raise SystemExit(
                f"Unexpected public API for {module_name}. "
                f"expected={sorted(expected)} actual={sorted(actual)}"
            )
        for attribute in contract.get("attributes", []):
            if not hasattr(module, attribute):
                raise SystemExit(f"Missing public attribute: {module_name}.{attribute}")

    if pyingestkit.__version__ != EXPECTED_PACKAGE_VERSION:
        raise SystemExit(
            "Unexpected package version during V1 RC qualification: "
            f"{pyingestkit.__version__}"
        )

    print(
        "OK: V1 public API inventory matches the governed manifest "
        f"for PyIngestKit {EXPECTED_PACKAGE_VERSION}"
    )


if __name__ == "__main__":
    main()
