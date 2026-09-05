from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.cli.app import app
from pyingestkit.core.registry import JobRegistry


class VerboseStep(Step):
    def execute(self, context: RunContext, data):
        logging.getLogger("pyingestkit.demo.verbose").debug("internal debug marker")
        return data


class Demo(Job):
    id = "demo.cli_history"

    def pipeline(self) -> Pipeline:
        return Pipeline([VerboseStep()])


class CliRunHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        registry = JobRegistry()
        registry.register(Demo())
        self.registry_patch = patch(
            "pyingestkit.cli.commands.run.get_registry", return_value=registry
        )
        self.registry_patch.start()

    def tearDown(self) -> None:
        self.registry_patch.stop()
        root = logging.getLogger()
        for handler in tuple(root.handlers):
            root.removeHandler(handler)
            handler.close()

    def test_run_then_runs_then_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.runner.isolated_filesystem(temp_dir=tmp):
            workspace = Path(tmp) / ".pyingest"
            run_result = self.runner.invoke(
                app, ["run", "demo.cli_history", "--workspace", str(workspace), "--json"]
            )
            self.assertEqual(run_result.exit_code, 0, run_result.output)
            payload = json.loads(run_result.stdout)
            self.assertTrue((workspace / "state" / "pyingest.sqlite3").is_file())

            runs_result = self.runner.invoke(app, ["runs", "--workspace", str(workspace), "--json"])
            self.assertEqual(runs_result.exit_code, 0, runs_result.output)
            runs = json.loads(runs_result.stdout)
            self.assertEqual(runs[0]["run_id"], payload["run_id"])

            status_result = self.runner.invoke(
                app,
                ["status", payload["run_id"][:8], "--workspace", str(workspace), "--json"],
            )
            self.assertEqual(status_result.exit_code, 0, status_result.output)
            status = json.loads(status_result.stdout)
            self.assertEqual(status["run"]["status"], "SUCCESS")
            self.assertEqual(status["steps"][0]["name"], "VerboseStep")

    def test_verbose_and_quiet_are_mutually_exclusive(self) -> None:
        result = self.runner.invoke(app, ["run", "demo.cli_history", "-v", "-q"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("mutually exclusive", result.output)

    def test_verbose_exposes_debug_console_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.runner.isolated_filesystem(temp_dir=tmp):
            result = self.runner.invoke(
                app, ["run", "demo.cli_history", "--workspace", tmp, "-v", "--json"]
            )
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("internal debug marker", result.stderr)
            self.assertNotIn("internal debug marker", result.stdout)
            json.loads(result.stdout)

    def test_quiet_suppresses_info_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.runner.isolated_filesystem(temp_dir=tmp):
            result = self.runner.invoke(
                app, ["run", "demo.cli_history", "--workspace", tmp, "-q", "--json"]
            )
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("Run started", result.stderr)
            json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
