import os
import subprocess
import sys
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_version(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "pyingestkit.cli.main", "--version"],
            cwd=project_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("0.1.0", completed.stdout)


if __name__ == "__main__":
    unittest.main()
