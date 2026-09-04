from __future__ import annotations

import unittest

import pyingestkit
from pyingestkit.targets import (
    LoadMode,
    PostgresTarget,
    Target,
    TargetCapabilities,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)


class TargetsPublicApiTests(unittest.TestCase):
    def test_a2_target_types_remain_public(self) -> None:
        expected = {
            "LoadMode",
            "PostgresTarget",
            "Target",
            "TargetCapabilities",
            "TargetLoadRequest",
            "TargetLoadResult",
            "TargetLoadStatus",
        }
        self.assertTrue(expected.issubset(set(pyingestkit.__all__)))
        self.assertIs(pyingestkit.Target, Target)
        self.assertIs(pyingestkit.PostgresTarget, PostgresTarget)
        self.assertIs(pyingestkit.TargetCapabilities, TargetCapabilities)
        self.assertIs(pyingestkit.TargetLoadRequest, TargetLoadRequest)
        self.assertIs(pyingestkit.TargetLoadResult, TargetLoadResult)
        self.assertIs(pyingestkit.TargetLoadStatus, TargetLoadStatus)
        self.assertIs(pyingestkit.LoadMode, LoadMode)

    def test_postgres_a2_capabilities_claim_copy_but_not_future_load_modes(self) -> None:
        capabilities = PostgresTarget.A2_CAPABILITIES
        self.assertTrue(capabilities.transactional)
        self.assertTrue(capabilities.append)
        self.assertTrue(capabilities.bulk_load)
        self.assertFalse(capabilities.truncate_load)
        self.assertFalse(capabilities.replace)
        self.assertFalse(capabilities.staging)


if __name__ == "__main__":
    unittest.main()
