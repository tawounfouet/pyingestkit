from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from pyingestkit.cli.app import app
from pyingestkit.cli.main import main as cli_main
from pyingestkit.core.registry import JobRegistry


class CliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_version(self) -> None:
        result = self.runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("0.6.0b1", result.output)
        self.assertNotIn("\x1b", result.output)

    def test_root_help(self) -> None:
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        for command in (
            "jobs",
            "inspect",
            "run",
            "runs",
            "status",
            "versions",
            "published",
            "replay",
        ):
            self.assertIn(command, result.output)

    def test_help_command(self) -> None:
        result = self.runner.invoke(app, ["help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("PyIngestKit", result.output)

    def test_jobs_json_with_no_plugins(self) -> None:
        with patch(
            "pyingestkit.cli.commands.jobs.get_registry_with_diagnostics",
            return_value=(JobRegistry(), ()),
        ):
            result = self.runner.invoke(app, ["jobs", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertNotIn("\x1b", result.stdout)

    def test_inspect_missing_job_id_is_validation_error(self) -> None:
        result = self.runner.invoke(app, ["inspect"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing argument", result.output)

    def test_console_entrypoint_loads_cwd_dotenv_without_overriding_os(self) -> None:
        key = "PYINGESTKIT_DOTENV_TEST_VALUE"
        previous = os.environ.get(key)
        original_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                (workspace / ".env").write_text(f"{key}=from-file\n", encoding="utf-8")
                os.environ[key] = "from-os"
                os.chdir(workspace)
                with patch("pyingestkit.cli.main.app") as mocked_app:
                    cli_main()
                self.assertEqual(os.environ[key], "from-os")
                mocked_app.assert_called_once_with(prog_name="pyingest")
        finally:
            os.chdir(original_cwd)
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

    def test_console_entrypoint_does_not_search_parent_dotenv(self) -> None:
        key = "PYINGESTKIT_DOTENV_PARENT_TEST_VALUE"
        previous = os.environ.pop(key, None)
        original_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                child = parent / "child"
                child.mkdir()
                (parent / ".env").write_text(f"{key}=from-parent\n", encoding="utf-8")
                os.chdir(child)
                with patch("pyingestkit.cli.main.app"):
                    cli_main()
                self.assertNotIn(key, os.environ)
        finally:
            os.chdir(original_cwd)
            if previous is not None:
                os.environ[key] = previous


if __name__ == "__main__":
    unittest.main()
