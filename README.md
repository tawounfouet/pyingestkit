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
- production-grade `pyingest` CLI powered by Typer and Rich
- stdlib-only ingestion runtime; Typer + Rich production-grade CLI

## Scope

PyIngestKit is an ingestion framework. It is **not** a scheduler, distributed executor, Data Platform, Data Catalog, AI framework, web application, or universal integration platform.

External tools decide **WHEN** to run. PyIngestKit owns **HOW TO INGEST**.


```bash
python3.12 -m venv .venv
source .venv/bin/activate

pip install -e .


# python -m pip install -e .
```
The ingestion runtime remains stdlib-only. Typer and Rich are installed as CLI dependencies and are isolated under `pyingestkit.cli`.

## CLI

```bash
pyingest --version
pyingest --help
pyingest help
pyingest jobs
pyingest inspect <job-id>
pyingest run <job-id> --workspace .pyingest

# Machine-readable output
pyingest jobs --json
pyingest inspect <job-id> --json
pyingest run <job-id> --json
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

After installing the project (which installs Typer and Rich for the CLI), run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Status

`0.1.1` is intentionally pre-stable. Public contracts may still evolve before `1.0.0`.
