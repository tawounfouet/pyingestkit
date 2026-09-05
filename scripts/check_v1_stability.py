from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from typer.main import get_command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyingestkit.deprecations as deprecations
import pyingestkit.errors as errors
import pyingestkit.logging as logging_api
import pyingestkit.plugins as plugins
from pyingestkit.cli.app import app
from pyingestkit.config import FileLoggingConfig, LogOutputFormat, load_config
from pyingestkit.config.loader import DEFAULT_CONFIG_FILES

CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "stability_v1.json"
PUBLIC_API_PATH = ROOT / "tests" / "contract" / "fixtures" / "public_api_v1.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _public_api() -> dict[str, Any]:
    return json.loads(PUBLIC_API_PATH.read_text(encoding="utf-8"))


@contextmanager
def _environment(**updates: str | None) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _check_plugins(contract: dict[str, Any]) -> None:
    expected = contract["plugins"]
    if plugins.ENTRY_POINT_GROUP != expected["entry_point_group"]:
        raise SystemExit("Plugin entry-point group changed")
    if expected["strict_library_default"] is not True:
        raise SystemExit("B1 contract must keep strict library discovery as the default")


def _check_configuration(contract: dict[str, Any]) -> None:
    expected = contract["configuration"]
    if list(DEFAULT_CONFIG_FILES) != expected["default_files"]:
        raise SystemExit(
            f"Default config filenames changed: expected={expected['default_files']} "
            f"actual={list(DEFAULT_CONFIG_FILES)}"
        )

    public_env = _public_api()["configuration"]["environment_variables"]
    if public_env != expected["environment_variables"]:
        raise SystemExit(
            f"Configuration environment inventory drifted: expected={expected['environment_variables']} "
            f"actual={public_env}"
        )

    with tempfile.TemporaryDirectory(prefix="pyingestkit-v1-b1-config-") as directory:
        config_path = Path(directory) / "config.yml"
        config_path.write_text("runtime:\n  workspace: from-yaml\n", encoding="utf-8")
        with _environment(PYINGEST_WORKSPACE="from-env"):
            config = load_config(config_path)
        if config.runtime.workspace != Path("from-env"):
            raise SystemExit("PYINGEST_WORKSPACE no longer overrides runtime.workspace")

    try:
        FileLoggingConfig(format=LogOutputFormat.RICH)
    except Exception:  # noqa: BLE001 - any Pydantic validation failure is acceptable here
        pass
    else:
        raise SystemExit("Rich file logging must be rejected; V1 file formats are plain/json")


def _command_surface() -> tuple[dict[str, dict[str, list[str]]], set[str]]:
    root = get_command(app)
    result: dict[str, dict[str, list[str]]] = {}
    for command_name, command in root.commands.items():
        arguments: list[str] = []
        options: list[str] = []
        for parameter in command.params:
            opts = list(getattr(parameter, "opts", ()))
            secondary = list(getattr(parameter, "secondary_opts", ()))
            if opts and opts[0].startswith("-"):
                options.extend(opts)
                options.extend(secondary)
            else:
                arguments.append(parameter.name)
        result[command_name] = {"arguments": arguments, "options": options}

    root_options = set(root.context_settings.get("help_option_names", ["--help"]))
    for parameter in root.params:
        root_options.update(getattr(parameter, "opts", ()))
        root_options.update(getattr(parameter, "secondary_opts", ()))
    return result, root_options


def _check_cli(contract: dict[str, Any]) -> None:
    expected = contract["cli"]
    actual_commands, root_options = _command_surface()
    if set(actual_commands) != set(expected["commands"]):
        raise SystemExit(
            f"CLI command set changed: expected={sorted(expected['commands'])} "
            f"actual={sorted(actual_commands)}"
        )

    for name, command_contract in expected["commands"].items():
        actual = actual_commands[name]
        if actual["arguments"] != command_contract["arguments"]:
            raise SystemExit(
                f"CLI arguments changed for {name}: expected={command_contract['arguments']} "
                f"actual={actual['arguments']}"
            )
        if set(actual["options"]) != set(command_contract["options"]):
            raise SystemExit(
                f"CLI options changed for {name}: expected={sorted(command_contract['options'])} "
                f"actual={sorted(actual['options'])}"
            )

    if root_options != set(expected["root_options"]):
        raise SystemExit(
            f"CLI root options changed: expected={sorted(expected['root_options'])} "
            f"actual={sorted(root_options)}"
        )
    forbidden = set(expected["forbidden_root_options"])
    if root_options & forbidden:
        raise SystemExit(f"Accidental completion options returned: {sorted(root_options & forbidden)}")


def _check_errors(contract: dict[str, Any]) -> None:
    expected = contract["errors"]
    if expected["canonical_module"] != errors.__name__:
        raise SystemExit("Canonical V1 error module changed")
    warning = getattr(deprecations, expected["deprecation_warning"])
    if not issubclass(warning, FutureWarning):
        raise SystemExit("PyIngestKitDeprecationWarning must remain visible by default")

    from pyingestkit.core.exceptions import PluginError as HistoricalPluginError
    from pyingestkit.sources.http import HttpError as HistoricalHttpError
    from pyingestkit.targets import TargetError as HistoricalTargetError

    if errors.PluginError is not HistoricalPluginError:
        raise SystemExit("Canonical PluginError identity changed")
    if errors.HttpError is not HistoricalHttpError:
        raise SystemExit("Canonical HttpError identity changed")
    if errors.TargetError is not HistoricalTargetError:
        raise SystemExit("Canonical TargetError identity changed")


def _check_observability(contract: dict[str, Any]) -> None:
    expected = contract["observability"]
    if set(logging_api.__all__) != set(expected["exports"]):
        raise SystemExit(
            f"Logging public exports changed: expected={sorted(expected['exports'])} "
            f"actual={sorted(logging_api.__all__)}"
        )
    redacted = logging_api.redact_text("postgresql://user:hunter2@db/app token=secret")
    if "hunter2" in redacted or "token=secret" in redacted:
        raise SystemExit("Logging redaction no longer masks URL or key/value credentials")
    if expected["redaction_marker"] not in redacted:
        raise SystemExit("Logging redaction marker changed")


def main() -> None:
    contract = _contract()
    if contract["schema_version"] != 1:
        raise SystemExit(f"Unsupported B1 stability contract schema: {contract['schema_version']!r}")
    _check_plugins(contract)
    _check_configuration(contract)
    _check_cli(contract)
    _check_errors(contract)
    _check_observability(contract)
    print("OK: V1 operational stability contract is intact (V1.0.0-b1)")


if __name__ == "__main__":
    main()
