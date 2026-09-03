import unittest

from pyingestkit import Job, Pipeline
from pyingestkit.core.registry import JobRegistry


class DemoJob(Job):
    id = "demo.registry"

    def pipeline(self) -> Pipeline:
        return Pipeline([])


class RegistryTests(unittest.TestCase):
    def test_register_and_get(self) -> None:
        registry = JobRegistry()
        job = DemoJob()
        registry.register(job)
        self.assertIs(registry.get("demo.registry"), job)
        self.assertEqual(len(registry), 1)

    def test_duplicate_rejected(self) -> None:
        registry = JobRegistry()
        registry.register(DemoJob())
        with self.assertRaises(ValueError):
            registry.register(DemoJob())


if __name__ == "__main__":
    unittest.main()
