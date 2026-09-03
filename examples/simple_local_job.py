from pathlib import Path
from typing import Any

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.runtime import Runner
from pyingestkit.sources import LocalSource


class FetchLocal(Step):
    def __init__(self, path: Path) -> None:
        self.source = LocalSource(path)

    def execute(self, context: RunContext, data: Any) -> Any:
        return self.source.fetch(context)


class DemoJob(Job):
    id = "demo.local_file"
    version = "0.1.0"
    description = "Minimal local ingestion example"

    def __init__(self, path: Path) -> None:
        self.path = path

    def pipeline(self) -> Pipeline:
        return Pipeline([FetchLocal(self.path)])


if __name__ == "__main__":
    sample = Path("sample.txt")
    sample.write_text("hello pyingestkit\n", encoding="utf-8")
    result = Runner(LocalArtifactStore(".pyingest")).run(DemoJob(sample))
    print(result)
