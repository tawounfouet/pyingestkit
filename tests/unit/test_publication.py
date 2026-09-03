import tempfile
import unittest
from pathlib import Path

from pyingestkit.publication import AtomicPublisher


class PublicationTests(unittest.TestCase):
    def test_atomic_publish_replaces_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.txt"
            destination = root / "published" / "current.txt"
            candidate.write_text("v2", encoding="utf-8")
            destination.parent.mkdir(parents=True)
            destination.write_text("v1", encoding="utf-8")
            AtomicPublisher().publish_file(candidate, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "v2")


if __name__ == "__main__":
    unittest.main()
