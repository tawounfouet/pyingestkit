from typer.testing import CliRunner

from pyingestkit.cli.app import app


def test_replay_command_is_exposed() -> None:
    result = CliRunner().invoke(app, ["replay", "--help"])
    assert result.exit_code == 0
    assert "--allow-version-change" in result.output
    assert "--no-verify" in result.output
