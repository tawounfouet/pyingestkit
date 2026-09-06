from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyingestkit

CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "stable_release_v1.json"
PUBLIC_API_PATH = ROOT / "tests" / "contract" / "fixtures" / "public_api_v1.json"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def main() -> None:
    contract = _json(CONTRACT_PATH)
    versions = contract["versions"]
    framework_version = versions["framework"]
    demo_version = versions["demo_package"]

    if contract["milestone"] != "V1.0.0":
        raise SystemExit("Stable release contract milestone drift")
    if contract["baseline"]["rc1_merge_sha"] != "e98a12cc3bbfb634d2fd2257f43049fa1e0333dd":
        raise SystemExit("Stable release is not anchored to the qualified RC1 merge baseline")
    if contract["baseline"]["upgrade_from"] != "0.6.0":
        raise SystemExit("Stable V1 must retain V0.6.0 as the executable upgrade baseline")

    if pyingestkit.__version__ != framework_version:
        raise SystemExit(
            f"Framework version drift: expected {framework_version}, got {pyingestkit.__version__}"
        )

    project = _read_toml(ROOT / "pyproject.toml")
    if project["project"].get("dynamic") != ["version"]:
        raise SystemExit("Framework package version must remain sourced from pyingestkit._version")

    demo_project = _read_toml(ROOT / "examples" / "plugin_package" / "pyproject.toml")["project"]
    if demo_project["version"] != demo_version:
        raise SystemExit(
            f"Demo package version drift: expected {demo_version}, got {demo_project['version']}"
        )
    expected_dependency = f"pyingestkit>={framework_version},<1.1"
    if expected_dependency not in demo_project["dependencies"]:
        raise SystemExit("Demo package stable dependency range drift: " + expected_dependency)

    for relative in contract["required_docs"] + contract["required_scripts"]:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Missing stable V1 governed file: {relative}")

    public_api = _json(PUBLIC_API_PATH)
    promotion = contract["public_api"]
    if promotion["promotion_from"] != "PUBLIC_STABLE_CANDIDATE":
        raise SystemExit("Unexpected V1 public API promotion source classification")
    if promotion["promotion_to"] != "PUBLIC_STABLE":
        raise SystemExit("Stable V1 must explicitly promote the governed candidate surface")
    if promotion["experimental_remains_experimental"] is not True:
        raise SystemExit("Stable V1 must keep explicitly experimental surfaces outside the 1.x promise")
    if not any(
        module.get("classification") == "PUBLIC_STABLE_CANDIDATE"
        for module in public_api["modules"].values()
    ):
        raise SystemExit("A1 public API inventory no longer contains its historical stable candidates")
    if any(
        module.get("classification") == "REMOVE_BEFORE_V1"
        for module in public_api["modules"].values()
    ):
        raise SystemExit("A REMOVE_BEFORE_V1 module survived into the stable release")

    wheel_smoke = (ROOT / "scripts" / "wheel_smoke_test.py").read_text(encoding="utf-8")
    for needle in (
        f'FRAMEWORK_VERSION = "{framework_version}"',
        f'DEMO_VERSION = "{demo_version}"',
    ):
        if needle not in wheel_smoke:
            raise SystemExit(f"Wheel smoke is not aligned to stable V1: {needle}")

    upgrade_smoke = (ROOT / "scripts" / "upgrade_smoke_test.py").read_text(encoding="utf-8")
    if f'TARGET_VERSION = "{framework_version}"' not in upgrade_smoke:
        raise SystemExit("V0.6 upgrade smoke is not aligned to stable V1")

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in contract["required_ci_jobs"]:
        if f"  {job}:" not in workflow:
            raise SystemExit(f"Missing stable V1 CI job: {job}")
    for artifact_name in contract["ci_artifact_names"]:
        if artifact_name not in workflow:
            raise SystemExit(f"Missing stable V1 CI artifact name: {artifact_name}")
    for stale in ("pyingestkit-v1.0.0rc1-source", "pyingestkit-v1.0.0rc1-dist"):
        if stale in workflow:
            raise SystemExit(f"Stable CI still publishes candidate artifact name: {stale}")

    release_notes = ROOT / "docs" / "releases" / "v1.0.0.md"
    release_text = release_notes.read_text(encoding="utf-8")
    if "1.0.0" not in release_text or "status: **stable**" not in release_text.lower():
        raise SystemExit("Stable V1 release notes do not clearly identify the stable state")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "V1.0.0 Stable" not in readme or "pyingestkit-v1.0.0-dist" not in readme:
        raise SystemExit("README does not advertise the V1.0.0 stable package/artifact state")

    release = contract["release"]
    if release["tag"] != "v1.0.0" or release["tag_kind"] != "annotated":
        raise SystemExit("Stable release tag contract must be annotated v1.0.0")
    if release["immutable"] is not True or "post-merge" not in release["creation_phase"]:
        raise SystemExit("Stable release tag governance must be immutable and post-merge")

    scope = contract["scope"]
    if any(
        scope[key] is not False
        for key in (
            "introduces_new_ingestion_provider",
            "introduces_orchestration_platform",
            "changes_persisted_schema_versions",
        )
    ):
        raise SystemExit("Stable V1 promotion must not expand product scope or persisted schemas")

    print(
        "OK: V1.0.0 stable release contract is intact "
        f"(framework={framework_version}, demo={demo_version}, rc1={versions['release_candidate']}, "
        "upgrade_from=0.6.0, tag=v1.0.0 post-merge)"
    )


if __name__ == "__main__":
    main()
