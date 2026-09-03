# PyIngestKit

**PyIngestKit** is a small, composable Python framework for reliable batch ingestion.

> Bring your source. Define your transformations. Declare your checks. PyIngestKit handles the plumbing.

This repository contains the **MVP V0.1** implementation defined by the PyIngestKit architecture:

- `Job`, `Step`, `Pipeline`, `RunContext`
- standardized `StepResult` / `RunResult`
- explicit runtime runner and lifecycle events
- `LocalSource`
- immutable `RawArtifact` with SHA-256
- `LocalArtifactStore`
- JSON `RunManifest`
- basic validation rules and reports
- atomic file publication
- `JobRegistry`
- plugin discovery through Python entry points
- minimal `pyingest` CLI
- zero mandatory third-party runtime dependencies

## Scope

PyIngestKit is an ingestion framework. It is **not** a scheduler, distributed executor, Data Platform, Data Catalog, AI framework, web application, or universal integration platform.

External tools decide **WHEN** to run. PyIngestKit owns **HOW TO INGEST**.

## Installation


```bash
python3.12 -m venv .venv
source .venv/bin/activate

pip install -e .


# python -m pip install -e .
```

No mandatory third-party runtime dependency is required.

## CLI

```bash
pyingest --version
pyingest jobs
pyingest inspect <job-id>
pyingest run <job-id> --workspace .pyingest
```

Jobs installed by other packages are discovered through:

```toml
[project.entry-points."pyingestkit.jobs"]
my_job = "my_package.jobs:job"
```

## Run workspace

```text
.pyingest/
└── runs/
    └── <namespace>/
        └── <job>/
            └── <run_id>/
                ├── raw/
                ├── staging/
                ├── candidate/
                ├── reports/
                └── manifest.json
```

## Tests

The MVP test suite only needs the Python standard library:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Status

`0.1.0` is intentionally pre-stable. Public contracts may still evolve before `1.0.0`.
