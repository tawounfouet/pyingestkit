from __future__ import annotations

import importlib
import json
import tomllib
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from pyingestkit.cli.app import app


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "tests" / "contract" / "fixtures" / "public_api_v1.json"


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_v1_public_api_manifest_has_expected_classification_vocabulary() -> None:
    data = _manifest()
    assert data["classifications"] == [
        "PUBLIC_STABLE_CANDIDATE",
        "PUBLIC_EXPERIMENTAL",
        "INTERNAL",
        "DEPRECATED",
        "REMOVE_BEFORE_V1",
    ]


def test_v1_public_namespace_exports_match_manifest_exactly() -> None:
    data = _manifest()
    for module_name, contract in data["modules"].items():
        module = importlib.import_module(module_name)
        actual = set(getattr(module, "__all__"))
        expected = set(contract["exports"])
        assert actual == expected, (
            f"Unexpected public exports for {module_name}: "
            f"expected={sorted(expected)} actual={sorted(actual)}"
        )
        for attribute in contract.get("attributes", []):
            assert hasattr(module, attribute), f"Missing public attribute {module_name}.{attribute}"
        for symbol in contract.get("experimental_symbols", []):
            assert symbol in expected
        for symbol in contract.get("stable_candidate_symbols", []):
            assert symbol in expected


def test_v1_exception_inventory_is_importable_and_keeps_replay_hierarchy() -> None:
    data = _manifest()
    error_contract = data["exceptions"]
    module = importlib.import_module(error_contract["module"])
    for symbol in error_contract["symbols"]:
        value = getattr(module, symbol)
        assert isinstance(value, type)
        assert issubclass(value, Exception)

    replay_error = getattr(module, "ReplayError")
    assert issubclass(getattr(module, "ReplayIntegrityError"), replay_error)
    assert issubclass(getattr(module, "ReplayMismatchError"), replay_error)
    assert issubclass(replay_error, getattr(module, "IngestionError"))


def test_v1_cli_command_names_match_manifest() -> None:
    data = _manifest()
    expected = set(data["cli"]["commands"])
    actual = {command.name for command in app.registered_commands if command.name is not None}
    assert actual == expected


def test_v1_cli_root_options_are_invokable() -> None:
    data = _manifest()
    runner = CliRunner()
    for option in data["cli"]["root_options"]:
        result = runner.invoke(app, [option])
        assert result.exit_code == 0, f"{option} failed: {result.output}"


def test_v1_python_support_and_optional_extra_names_match_packaging() -> None:
    data = _manifest()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    expected_python = data["python_support"]["versions"]
    classifiers = set(project["project"]["classifiers"])
    for version in expected_python:
        assert f"Programming Language :: Python :: {version}" in classifiers

    extras = set(project["project"]["optional-dependencies"])
    assert extras == set(data["optional_extras"]["names"])


def test_v1_plugin_entry_point_group_is_present_in_reference_pack() -> None:
    data = _manifest()
    demo = tomllib.loads(
        (ROOT / "examples" / "plugin_package" / "pyproject.toml").read_text(encoding="utf-8")
    )
    groups = demo["project"]["entry-points"]
    assert data["plugins"]["entry_point_group"] in groups
