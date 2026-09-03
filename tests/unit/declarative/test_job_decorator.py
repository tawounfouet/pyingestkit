from __future__ import annotations

import unittest

from pyingestkit import job, step
from pyingestkit.declarative import JobDefinition


class JobDecoratorTests(unittest.TestCase):
    def test_job_builds_imperative_job(self) -> None:
        @step(name="First")
        def first(data=None):
            return data

        @job(id="demo.declarative", version="1.2.3", description="demo")
        def pipeline() -> None:
            first()

        self.assertIsInstance(pipeline, JobDefinition)
        built = pipeline.build()
        self.assertEqual(built.id, "demo.declarative")
        self.assertEqual(built.version, "1.2.3")
        self.assertEqual([item.step_name for item in built.pipeline()], ["First"])
        self.assertEqual(getattr(built, "definition_style"), "declarative")


if __name__ == "__main__":
    unittest.main()
