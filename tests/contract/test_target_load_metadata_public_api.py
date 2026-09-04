from __future__ import annotations

import unittest

from pyingestkit.metadata import (
    TargetLoadMetadataCapability,
    TargetLoadRecord,
)


class TargetLoadMetadataPublicApiTests(unittest.TestCase):
    def test_b1_metadata_types_are_namespaced_and_importable(self) -> None:
        self.assertEqual(TargetLoadMetadataCapability.__name__, "TargetLoadMetadataCapability")
        self.assertEqual(TargetLoadRecord.__name__, "TargetLoadRecord")


if __name__ == "__main__":
    unittest.main()
