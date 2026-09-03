from __future__ import annotations

from pathlib import Path

from pyingestkit import RunContext, Runner, job, step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.sources import LocalSource


@step(name="FetchLocal")
def fetch_local(context: RunContext):
    return LocalSource(Path(str(context.parameter("path")))).fetch(context)


@job(id="demo.local_file", version="0.1.0")
def local_file_job() -> None:
    fetch_local()


if __name__ == "__main__":
    workspace = Path(".pyingest")
    result = Runner(
        LocalArtifactStore(workspace),
        metadata_store=SQLiteMetadataStore.for_workspace(workspace),
    ).run(
        local_file_job.build(),
        parameters={"path": "examples/plugin_package/data/sample.txt"},
    )
    print(result)
