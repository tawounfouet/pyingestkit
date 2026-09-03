# PyIngestKit

**PyIngestKit** is a composable Python framework for reliable batch ingestion.

> Bring your source. Define your transformations. Declare your checks. PyIngestKit handles the plumbing.

This repository contains the **MVP V0.1.2** implementation:

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
- Typer + Rich production-grade CLI
- Pydantic + PyYAML validated project configuration

## Scope

PyIngestKit is an ingestion framework. It is **not** a scheduler, distributed executor, Data Platform, Data Catalog, AI framework, web application, or universal integration platform.

External tools decide **WHEN** to run. PyIngestKit owns **HOW TO INGEST**.

## Runtime dependencies

PyIngestKit intentionally uses established third-party packages when they improve framework quality and reduce bespoke infrastructure code:

```text
Typer     → CLI contracts
Rich      → terminal UX
Pydantic  → validated configuration models
PyYAML    → YAML configuration loading
```

The project does **not** enforce a zero-third-party-dependency constraint. Dependency additions remain governed by ADR-010 and must have a clear framework-level purpose.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Development installation:

```bash
python -m pip install -e ".[dev]"
```

## CLI

```bash
pyingest --version
pyingest --help
pyingest help
pyingest jobs
pyingest inspect <job-id>
pyingest run <job-id>

# Machine-readable output
pyingest jobs --json
pyingest inspect <job-id> --json
pyingest run <job-id> --json
```

Machine-readable output is plain JSON without ANSI/Rich formatting.

## YAML configuration

Create `pyingest.yml`:

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: false
  parameters:
    source: local
```

Then:

```bash
pyingest run <job-id> --config pyingest.yml
```

CLI options override YAML values.

## Plugin discovery

Jobs installed by other packages are discovered through Python entry points:

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

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Or, after installing the development dependencies:

```bash
pytest
```

## Status

`0.1.2` is intentionally pre-stable. Public contracts may still evolve before `1.0.0`.
