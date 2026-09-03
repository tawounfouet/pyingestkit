from __future__ import annotations

import unittest
from unittest.mock import patch

from pyingestkit import Job, Pipeline
from pyingestkit.plugins.discovery import discover_plugins


class Healthy(Job):
    id = "demo.healthy"
    def pipeline(self) -> Pipeline:
        return Pipeline([])


class FakeEntryPoint:
    def __init__(self, name, value=None, error=None):
        self.name = name
        self.value = value
        self.error = error
    def load(self):
        if self.error:
            raise self.error
        return self.value


class PluginIsolationTests(unittest.TestCase):
    def test_broken_plugin_does_not_hide_healthy_plugin(self) -> None:
        points = (
            FakeEntryPoint("healthy", Healthy()),
            FakeEntryPoint("broken", error=ImportError("missing dependency")),
        )
        with patch("pyingestkit.plugins.discovery._entry_points", return_value=points):
            report = discover_plugins()
        self.assertEqual([job.id for job in report.jobs], ["demo.healthy"])
        self.assertEqual(len(report.failures), 1)
        self.assertEqual(report.failures[0].entry_point, "broken")


if __name__ == "__main__":
    unittest.main()
