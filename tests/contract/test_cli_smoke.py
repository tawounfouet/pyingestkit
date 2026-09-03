from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from pyingestkit.cli.app import app
from pyingestkit.core.registry import JobRegistry


class CliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_version(self) -> None:
        result = self.runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("0.1.3", result.output)
        self.assertNotIn("\x1b", result.output)

    def test_root_help(self) -> None:
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("jobs", result.output)
        self.assertIn("inspect", result.output)
        self.assertIn("run", result.output)

    def test_help_command(self) -> None:
        result = self.runner.invoke(app, ["help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("PyIngestKit", result.output)

    def test_jobs_json_with_no_plugins(self) -> None:
        # Keep this contract deterministic even when unrelated PyIngestKit plugins
        # are installed in the developer/test environment.
        with patch(
            "pyingestkit.cli.commands.jobs.get_registry",
            return_value=JobRegistry(),
        ):
            result = self.runner.invoke(app, ["jobs", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output), [])
        self.assertNotIn("\x1b", result.output)

    def test_inspect_missing_job_id_is_validation_error(self) -> None:
        result = self.runner.invoke(app, ["inspect"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing argument", result.output)


if __name__ == "__main__":
    unittest.main()
