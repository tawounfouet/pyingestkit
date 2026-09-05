from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyingestkit

CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "release_candidate_v1.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def main() -> None:
    contract = _contract()
    versions = contract["versions"]
    framework_version = versions["framework"]
    demo_version = versions["demo_package"]

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
        raise SystemExit(
            "Demo package must depend on the V1 RC framework range: " + expected_dependency
        )

    for relative in contract["required_docs"] + contract["required_scripts"]:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Missing RC1 governed file: {relative}")

    wheel_smoke = (ROOT / "scripts" / "wheel_smoke_test.py").read_text(encoding="utf-8")
    for needle in (
        f'FRAMEWORK_VERSION = "{framework_version}"',
        f'DEMO_VERSION = "{demo_version}"',
    ):
        if needle not in wheel_smoke:
            raise SystemExit(f"Wheel smoke is not aligned to RC1: {needle}")

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in contract["required_ci_jobs"]:
        if f"  {job}:" not in workflow:
            raise SystemExit(f"Missing RC1 CI job: {job}")
    for artifact_name in contract["ci_artifact_names"]:
        if artifact_name not in workflow:
            raise SystemExit(f"Missing RC1 CI artifact name: {artifact_name}")
    if "pyingestkit-v0.6.0" in workflow or "Upload V0.6.0" in workflow:
        raise SystemExit("RC1 CI still publishes V0.6.0-named artifacts")

    release_notes = ROOT / "docs" / "releases" / f"v{framework_version}.md"
    if not release_notes.is_file():
        raise SystemExit(f"Missing V1 RC1 release notes: {release_notes.relative_to(ROOT)}")
    release_text = release_notes.read_text(encoding="utf-8")
    if framework_version not in release_text or "not stable" not in release_text.lower():
        raise SystemExit("V1 RC1 release notes do not clearly identify the candidate state")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "V1.0.0 RC1" not in readme or framework_version not in readme:
        raise SystemExit("README does not advertise the V1.0.0 RC1 candidate state")

    if contract["scope"]["creates_stable_tag"] is not False:
        raise SystemExit("RC1 governance must not claim that stable v1.0.0 has been created")

    print(
        "OK: V1.0.0-rc1 release candidate contract is intact "
        f"(framework={framework_version}, demo={demo_version}, upgrade_from=0.6.0)"
    )


if __name__ == "__main__":
    main()
