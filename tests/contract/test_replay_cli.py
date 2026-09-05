from __future__ import annotations

from inspect import signature

from typer.testing import CliRunner

from pyingestkit.cli.app import app
from pyingestkit.cli.commands.replay import replay_command


def test_replay_command_is_exposed() -> None:
    result = CliRunner().invoke(app, ["replay", "--help"])
    assert result.exit_code == 0

    parameters = signature(replay_command).parameters
    assert "source_run_id" in parameters
    assert parameters["source_run_id"].default is None
    assert "allow_version_change" in parameters
    assert "no_verify" in parameters
