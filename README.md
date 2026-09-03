# PyIngestKit

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

This repository contains **V0.1.6 — Foundation Persistence & Quality Hardening**, the V0.1.x foundation candidate that must pass `make verify` before V0.2 acquisition capabilities begin.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed DAG scheduler, a Data Platform, a Data Catalog, an IAM platform, or an AI/agent framework.

## What V0.1.6 provides

- recommended declarative `@job` / `@step` API;
- advanced imperative `Job` / `Step` / `Pipeline` API;
- one runtime (`Runner`) for both APIs;
- Typer + Rich CLI;
- Python entry-point job plugins;
- unified `.pyingest/` workspace;
- immutable RAW artifacts with SHA-256;
- manifest generation with automatic RAW artifact registration;
- `MetadataStore` abstraction;
- SQLite metadata backend by default;
- SQLAlchemy 2.x Core as the internal metadata persistence engine;
- optional PostgreSQL metadata adapter (`pyingestkit[postgres]` + psycopg);
- persisted runs, steps, artifacts, validations, publications, and structural runtime events;
- Rich/plain/JSON logging, rotating files, contextual logging, secret redaction;
- `-v/--verbose`, `-q/--quiet`;
- `pyingest runs` and `pyingest status`;
- plugin failure isolation;
- basic validation and atomic publication primitives.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Install the bundled demo job pack:

```bash
python -m pip install -e examples/plugin_package
```

## Recommended API — decorators

```python
from pyingestkit import RunContext, job, step

@step(name="FetchLocal")
def fetch_local(context: RunContext):
    ...

@step
def normalize(data):
    ...

@job(
    id="public.postal_codes",
    version="1.0.0",
    description="Official postal-code ingestion",
)
def postal_codes() -> None:
    fetch_local()
    normalize()
```

A decorated job compiles to the same imperative `Job`/`Pipeline` model used by `Runner`.

Direct unit testing remains explicit:

```python
normalize.fn(rows)
```

Calling `normalize(...)` outside a `@job` build is rejected to avoid hidden execution semantics.

### Guardrail

The decorator API is a deterministic **sequential pipeline builder**, not a distributed DAG engine. Generic scheduler semantics, parallel workers, sensors, branching and orchestration remain out of scope.

## Advanced API — imperative

```python
from pyingestkit import Job, Pipeline, RunContext, Step

class Fetch(Step):
    def execute(self, context: RunContext, data):
        ...

class MyJob(Job):
    id = "public.example"

    def pipeline(self) -> Pipeline:
        return Pipeline([Fetch()])
```

## CLI

```bash
pyingest --version
pyingest --help
pyingest jobs
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs
pyingest status <run-id-or-prefix>
```

Verbose / quiet execution:

```bash
pyingest run demo.local_file -v --param path=examples/plugin_package/data/sample.txt
pyingest run demo.local_file -q --param path=examples/plugin_package/data/sample.txt
```

Machine-readable output remains clean on stdout:

```bash
pyingest jobs --json
pyingest inspect demo.local_file --json
pyingest run demo.local_file --json --param path=examples/plugin_package/data/sample.txt
pyingest runs --json
pyingest status <run-id> --json
```

Operational logs are written to stderr.

## Unified workspace

```text
.pyingest/
├── state/
│   └── pyingest.sqlite3
├── logs/
│   └── pyingest.log
├── runs/
│   └── <namespace>/<job>/<run_id>/
│       ├── raw/
│       ├── staging/
│       ├── candidate/
│       ├── reports/
│       └── manifest.json
└── published/
```

A plugin does not silently select its own global workspace. Alternative workspaces are explicit runtime configuration.

## ArtifactStore vs MetadataStore

```text
ArtifactStore                         MetadataStore
─────────────                         ─────────────
RAW payloads                          runs
staging/candidate files               steps
reports                               artifact metadata
manifests                             validations
published datasets                    publications
                                      runtime events
```

The manifest remains the portable run snapshot. MetadataStore is the queryable historical index. Neither replaces the other.

### SQLite default

```yaml
metadata:
  backend: sqlite
```

By default the database is resolved relative to the effective workspace:

```text
.pyingest/state/pyingest.sqlite3
```

### PostgreSQL adapter

```bash
python -m pip install -e ".[postgres]"
export PYINGEST_DATABASE_URL='postgresql://...'
```

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL
```

Secrets are referenced by environment variable name, not embedded in versioned YAML.

## Logging convention

Terminal output follows the stable human convention:

```text
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file] Run started
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file step=FetchLocal] Step started
2026-09-03 17:42:03  DEBUG   [run=785c1cdc job=demo.local_file step=FetchLocal] RAW artifact written
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file step=FetchLocal] Step succeeded 0.002s
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file] Run succeeded 0.003s
```

Terminal timestamps use local time; JSON logs and metadata keep timezone-aware ISO-8601 timestamps and full run UUIDs. Common secret patterns and secret-looking runtime parameter keys are redacted.

Operational DEBUG/INFO logs are not copied wholesale into SQLite. Only structural runtime events are persisted.

## Configuration

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: false
  parameters: {}

metadata:
  backend: sqlite

logging:
  level: INFO
  format: rich
  console: true
  file:
    enabled: true
    path: .pyingest/logs/pyingest.log
    level: DEBUG
    format: json
    max_bytes: 10000000
    backup_count: 5
```

Runtime parameter precedence:

```text
framework defaults
      ↓
YAML
      ↓
--params-json
      ↓
--param/-p
      ↓
explicit CLI runtime options
```

## Demo

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs
```

The demo plugin itself is authored with `@step` / `@job` and exposes a `JobDefinition` through the `pyingestkit.jobs` entry-point group.

## Persistence implementation guardrail

`MetadataStore` is the framework contract. SQLAlchemy is an **internal persistence detail**:

```text
Runner / CLI
    ↓
MetadataStore
    ↓
SQLAlchemy Core
   ├── SQLite
   └── PostgreSQL + psycopg
```

Domain records (`RunRecord`, `StepRecord`, etc.) remain plain Python dataclasses. PyIngestKit does not expose SQLAlchemy sessions, declarative models, columns, or engines through its top-level job API. Peewee is deliberately not introduced: one persistence engine is enough. Alembic remains deferred until schema migration requirements are demonstrated by real releases.

SQLite enables foreign keys, WAL journal mode and a bounded busy timeout. PostgreSQL remains selected only through the `MetadataStore` adapter and a DSN sourced from an environment variable.

## Quality gates

```bash
make test
make quality
make security
make build
make verify
```

`make verify` is the operational Foundation freeze gate. It aggregates functional tests, public API/compile checks, Ruff lint + formatting, Mypy strict typing, Bandit, pip-audit and package builds. V0.2 must not start while this command is red in the reference CI environment.

## V0.2 boundary

Only after this foundation remains green should V0.2 add acquisition capabilities:

- HTTP source/client;
- retry policy;
- CSV parser;
- JSON parser;
- Dataset Contracts.

The complete stabilization rationale and guardrails are documented under `docs/architecture/foundation-stabilization-v0.1xx.md`.
