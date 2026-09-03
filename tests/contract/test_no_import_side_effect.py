import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ImportContractTests(unittest.TestCase):
    def test_import_creates_no_files(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        src = project_root / "src"
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(src)
            before = set(Path(tmp).iterdir())
            subprocess.run(
                [sys.executable, "-c", "import pyingestkit"],
                cwd=tmp,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            after = set(Path(tmp).iterdir())
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
