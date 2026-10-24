"""Unit tests for the CLI doctor diagnostics command."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from pyingestkit.cli.app import app
from pyingestkit.cli.commands.doctor import collect_doctor_report

runner = CliRunner()


def test_doctor_report_collection() -> None:
    report = collect_doctor_report()
    assert report.pyingestkit_version
    assert report.python_version
    assert report.python_supported is True
    assert len(report.core_dependencies) >= 3
    assert len(report.optional_extras) >= 6

    # Verify dict representation
    data = report.to_dict()
    assert data["status"] in ("healthy", "unhealthy")
    assert "pyingestkit" in data
    assert "runtime" in data
    assert "environment" in data


def test_doctor_command_json_output() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0, f"doctor --json failed: {result.output}"

    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"
    assert "version" in parsed["pyingestkit"]
    assert "python_version" in parsed["runtime"]
    assert isinstance(parsed["core_dependencies"], list)
    assert isinstance(parsed["optional_extras"], list)


def test_doctor_command_human_output() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, f"doctor failed: {result.output}"
    assert "PyIngestKit Doctor" in result.output
    assert "Core Runtime Dependencies" in result.output
    assert "Optional Provider Extras" in result.output


def test_doctor_unhealthy_when_python_unsupported() -> None:
    with patch("sys.version_info", (3, 9, 0)):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "unsupported" in result.output.lower()
