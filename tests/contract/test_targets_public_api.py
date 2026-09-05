from __future__ import annotations

import unittest

import pyingestkit
from pyingestkit.targets import (
    IdempotencyAction,
    IdempotencyPolicy,
    LoadMode,
    PostgresTarget,
    Target,
    TargetCapabilities,
    TargetLoadDecision,
    TargetLoadExecutor,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)


class TargetsPublicApiTests(unittest.TestCase):
    def test_b2_target_types_are_top_level_and_namespaced(self) -> None:
        expected = {
            "IdempotencyAction",
            "IdempotencyPolicy",
            "LoadMode",
            "PostgresTarget",
            "Target",
            "TargetCapabilities",
            "TargetLoadDecision",
            "TargetLoadExecutor",
            "TargetLoadRequest",
            "TargetLoadResult",
            "TargetLoadStatus",
        }
        self.assertTrue(expected.issubset(set(pyingestkit.__all__)))
        self.assertIs(pyingestkit.Target, Target)
        self.assertIs(pyingestkit.PostgresTarget, PostgresTarget)
        self.assertIs(pyingestkit.TargetCapabilities, TargetCapabilities)
        self.assertIs(pyingestkit.TargetLoadDecision, TargetLoadDecision)
        self.assertIs(pyingestkit.TargetLoadExecutor, TargetLoadExecutor)
        self.assertIs(pyingestkit.TargetLoadRequest, TargetLoadRequest)
        self.assertIs(pyingestkit.TargetLoadResult, TargetLoadResult)
        self.assertIs(pyingestkit.TargetLoadStatus, TargetLoadStatus)
        self.assertIs(pyingestkit.LoadMode, LoadMode)
        self.assertIs(pyingestkit.IdempotencyAction, IdempotencyAction)
        self.assertIs(pyingestkit.IdempotencyPolicy, IdempotencyPolicy)

    def test_postgres_b2_capabilities_enable_content_load_modes_without_future_features(
        self,
    ) -> None:
        capabilities = PostgresTarget.B2_CAPABILITIES
        self.assertTrue(capabilities.transactional)
        self.assertTrue(capabilities.append)
        self.assertTrue(capabilities.bulk_load)
        self.assertTrue(capabilities.truncate_load)
        self.assertTrue(capabilities.replace)
        self.assertFalse(capabilities.upsert)
        self.assertFalse(capabilities.staging)


if __name__ == "__main__":
    unittest.main()
