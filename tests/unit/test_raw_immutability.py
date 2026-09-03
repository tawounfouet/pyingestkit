from __future__ import annotations

import tempfile
import unittest
from uuid import uuid4

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.exceptions import StorageError


class RawImmutabilityTests(unittest.TestCase):
    def test_same_raw_name_cannot_be_overwritten_within_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            run_id = uuid4()
            store.write_raw("demo.raw", run_id, name="x.txt", data=b"one", source_uri="memory://one")
            with self.assertRaises(StorageError):
                store.write_raw("demo.raw", run_id, name="x.txt", data=b"two", source_uri="memory://two")


if __name__ == "__main__":
    unittest.main()
