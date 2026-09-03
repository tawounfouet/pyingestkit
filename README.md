# PyIngestKit

**PyIngestKit** is a composable Python framework for reliable batch ingestion.

> Bring your source. Define your transformations. Declare your checks. PyIngestKit handles the plumbing.

This repository contains the **MVP V0.1.3** implementation:

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
- repeatable typed runtime parameters through `--param/-p`
- a real installable demo job pack under `examples/plugin_package`

## Scope

PyIngestKit is an ingestion framework. It is **not** a scheduler, distributed executor, Data Platform, Data Catalog, AI framework, web application, or universal integration platform.

External tools decide **WHEN** to run. PyIngestKit owns **HOW TO INGEST**.

## Runtime dependencies

PyIngestKit intentionally uses established third-party packages when they improve framework quality and reduce bespoke infrastructure code:

```text
Typer     → CLI contracts
Rich      → terminal UX
Pydantic  → validated configuration models
PyYAML    → YAML configuration and typed CLI parameter parsing
```

Dependency additions are governed by ADR-010 and must have a clear framework-level purpose.

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
```

Machine-readable output:

```bash
pyingest jobs --json
pyingest inspect <job-id> --json
pyingest run <job-id> --json
```

Machine-readable output is plain JSON without ANSI/Rich formatting.

## Project YAML configuration

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

Runtime precedence is:

```text
framework defaults
        ↓
YAML configuration
        ↓
--params-json
        ↓
--param / -p
        ↓
explicit CLI runtime options
```

Repeatable parameters can be provided directly:

```bash
pyingest run <job-id> \
  --param path=data/input.csv \
  --param retries=3 \
  --param enabled=true
```

Values use YAML scalar semantics, so integers and booleans remain typed.

## Plugin discovery

PyIngestKit deliberately ships with **no business job inside the framework package**.

Installed job packs are discovered through Python entry points:

```toml
[project.entry-points."pyingestkit.jobs"]
my_job = "my_package.jobs:job"
```

A plugin entry point may expose a `Job` instance, a zero-argument `Job` subclass, or a zero-argument factory returning a `Job`.

## Install the bundled demo job pack

The repository contains a real, independently installable example package:

```text
examples/plugin_package/
├── pyproject.toml
├── demo.yml
├── data/sample.txt
└── src/pyingestkit_demo_jobs/
    ├── __init__.py
    └── local_file.py
```

Install it after PyIngestKit:

```bash
python -m pip install -e examples/plugin_package
```

Now the CLI discovers the job through `importlib.metadata`:

```bash
pyingest jobs
pyingest jobs --json
pyingest inspect demo.local_file
```

Run it using the provided YAML configuration:

```bash
pyingest run demo.local_file \
  --config examples/plugin_package/demo.yml
```

Or without YAML:

```bash
pyingest run demo.local_file \
  --param path=examples/plugin_package/data/sample.txt
```

The plugin is zero-argument at discovery time. Runtime values such as the source path are read from `RunContext.parameters`, keeping plugin discovery independent from execution parameters.

## Standalone example

The repository also keeps a direct Python example:

```bash
python examples/simple_local_job.py
```

This demonstrates the Python API directly. It is separate from plugin discovery.

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

The demo uses `.pyingest-demo/` when executed with `examples/plugin_package/demo.yml`.

## Tests

Standard-library test runner:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

With development dependencies installed:

```bash
pytest
ruff check src tests examples/plugin_package/src examples/plugin_package/tests
mypy src/pyingestkit
```

The demo package also has its own test:

```bash
PYTHONPATH=examples/plugin_package/src python -m unittest discover \
  -s examples/plugin_package/tests -v
```

## Status

`0.1.3` is intentionally pre-stable. Public contracts may still evolve before `1.0.0`.
