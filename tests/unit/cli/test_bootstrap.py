"""Unit tests for the guarded CLI bootstrap module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyingestkit.cli import bootstrap
from pyingestkit.cli.exit_codes import ExitCode


def test_missing_dependencies_returns_11_and_clean_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When typer or rich is missing, bootstrap must exit with code 11 without a traceback."""

    def mock_find_spec(name: str) -> None:
        if name in ("typer", "rich"):
            return None
        return MagicMock()

    with patch("importlib.util.find_spec", side_effect=mock_find_spec):
        exit_code = bootstrap.main(argv=["--help"])

    assert exit_code == int(ExitCode.MISSING_OPTIONAL_DEPENDENCY)
    captured = capsys.readouterr()
    assert "PyIngestKit CLI dependencies missing: typer, rich" in captured.err
    assert 'pip install "pyingestkit[cli]"' in captured.err


def test_broken_pipe_is_intercepted_gracefully() -> None:
    """BrokenPipeError should cleanly return ExitCode.BROKEN_PIPE without traceback."""
    with patch("pyingestkit.cli.app.app", side_effect=BrokenPipeError):
        code = bootstrap.main(argv=["--help"])

    assert code == int(ExitCode.BROKEN_PIPE)


def test_keyboard_interrupt_returns_130() -> None:
    """KeyboardInterrupt (Ctrl+C) should cleanly return ExitCode.INTERRUPTED."""
    with patch("pyingestkit.cli.app.app", side_effect=KeyboardInterrupt):
        code = bootstrap.main(argv=["jobs"])

    assert code == int(ExitCode.INTERRUPTED)


def test_system_exit_code_is_propagated() -> None:
    """SystemExit codes raised by Typer should be preserved."""
    with patch("pyingestkit.cli.app.app", side_effect=SystemExit(2)):
        code = bootstrap.main(argv=["invalid-command"])

    assert code == 2


def test_detect_prog_name() -> None:
    """Verify that prog_name resolves to pik, pyingest, or pyingestkit correctly."""
    with patch("sys.argv", ["/usr/local/bin/pik", "jobs"]):
        assert bootstrap._detect_prog_name() == "pik"

    with patch("sys.argv", ["/usr/local/bin/pyingest", "jobs"]):
        assert bootstrap._detect_prog_name() == "pyingest"

    with patch("sys.argv", ["/usr/local/bin/pyingestkit", "jobs"]):
        assert bootstrap._detect_prog_name() == "pyingestkit"

    with patch("sys.argv", ["/usr/local/bin/other", "jobs"]):
        assert bootstrap._detect_prog_name() == "pik"


def test_load_local_dotenv_checks_infra_envs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that _load_local_dotenv checks infra/envs/.env.<profile>."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYINGEST_ENV", "stg")

    infra_envs = tmp_path / "infra" / "envs"
    infra_envs.mkdir(parents=True)
    env_stg = infra_envs / ".env.stg"
    env_stg.write_text("TEST_VAR_FROM_INFRA=loaded_success\n", encoding="utf-8")

    bootstrap._load_local_dotenv()
    import os

    assert os.getenv("TEST_VAR_FROM_INFRA") == "loaded_success"
