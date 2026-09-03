from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit.config import load_config
from pyingestkit.core.exceptions import ConfigurationError


class ConfigTests(unittest.TestCase):
    def test_load_valid_yaml_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text(
                """
runtime:
  workspace: .work
  fixture_mode: true
  parameters:
    source: fixture
""".strip(),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.runtime.workspace, Path(".work"))
            self.assertTrue(config.runtime.fixture_mode)
            self.assertEqual(config.runtime.parameters["source"], "fixture")

    def test_unknown_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyingest.yml"
            path.write_text("unknown: true\n", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
