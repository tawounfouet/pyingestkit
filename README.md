# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Foundation](https://img.shields.io/badge/foundation-v0.1.6%20frozen-success.svg)](CHANGELOG.md)

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

This repository contains **V0.2.0 — Acquisition Release**, the first stable V0.2 release built on the frozen V0.1.6 Foundation. It connects HTTP acquisition, bounded retry, immutable RAW/provenance, CSV/JSON parsing, dependency-neutral datasets, dataset contracts, runtime validation evidence, manifests, metadata and events into complete reference slices.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed DAG scheduler, a Data Platform, a Data Catalog, an IAM platform, or an AI/agent framework.

## What V0.2.0 provides

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
- basic validation and atomic publication primitives;
- framework-owned synchronous HTTP acquisition through `HttpSource` / `HttpxClient`;
- conservative bounded retries through `RetryPolicy`, including `Retry-After`;
- sanitized HTTP provenance associated with immutable RAW artifacts;
- dependency-neutral `Dataset`;
- structural `CsvParser` and `JsonParser`;
- `FieldContract` / `DatasetContract` validation without business normalization;
- runtime-observed `ValidationResult` persisted to manifest/metadata/events.

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
pyingest inspect demo.http_csv
pyingest inspect demo.http_json
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
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

## V0.2.0-a2 — HTTP → RAW acquisition

Alpha 2 closes the first complete acquisition loop without introducing parsers:

```text
HttpSource
    │
    ▼
HttpClient / HttpxClient
    │
    ├── RetryPolicy
    │
    ▼
HTTP response bytes
    │
    ▼
immutable RawArtifact + SHA-256
    │
    ├── manifest.json
    └── MetadataStore
```

Example framework usage inside a job step:

```python
from pyingestkit.sources.http import HttpSource

artifact = HttpSource(
    "https://data.example.org/export.bin",
    headers={"Authorization": "Bearer ..."},
).fetch(context)
```

The returned `RawArtifact` records `source_uri`, `resolved_url`, HTTP status, content type, ETag, Last-Modified, retrieval time, byte size and SHA-256. Only a narrow provenance allow-list is persisted: authorization/cookie/API-key/token headers are never copied into RAW metadata or the manifest, and secret-looking URL/query values are redacted before persistence.

HTTP-specific relational metadata lives in `artifact_http_provenance`, leaving the generic `artifacts` table backward-compatible with the Foundation / Alpha 1 schema.

## V0.2.0-b1 — Dataset + CSV/JSON + Contracts

Beta 1 adds the first structured-data layer above RAW artifacts:

```text
RawArtifact
     │
     ▼
   Parser
 ┌───┴────┐
 ▼        ▼
CSV      JSON
 └───┬────┘
     ▼
  Dataset
     │
     ▼
DatasetContract
```

`Dataset` is a PyIngestKit-owned, dependency-neutral container. It is deliberately **not** a Pandas, Polars, or Arrow abstraction. `CsvParser` preserves CSV cells as strings; `JsonParser` preserves JSON-native values. Neither parser trims, renames, enriches, flattens, or performs business type conversion.

```python
from pyingestkit import CsvParser, DatasetContract, FieldContract

dataset = CsvParser().parse(raw_artifact)
result = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=str, unique=True),
        FieldContract("name", nullable=False, expected_type=str),
    ),
    allow_extra_fields=False,
    min_rows=1,
).validate(dataset)

if not result.is_valid:
    ...
```

The boundary is explicit: `Parser != business normalizer`, and `DatasetContract` validates without mutating the dataset.

## Demo

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
pyingest inspect demo.local_file
pyingest inspect demo.http_csv
pyingest inspect demo.http_json
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
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
make wheel-smoke
make release-check
```

`make verify` remains the complete source gate inherited from the Foundation: functional tests, public API/compile checks, Ruff lint + formatting, Mypy strict typing, Bandit, pip-audit and package builds. For V0.2.0, the release process adds a fresh-environment wheel smoke test over the built framework and demo-job wheels before artifacts are accepted.

## V0.2.0 acquisition release

V0.2.0 completes the acquisition milestone that was built incrementally on the frozen Foundation:

- HTTP source/client — **released**;
- retry policy — **released**;
- HTTP → immutable RAW + provenance — **released**;
- CSV parser — **released**;
- JSON parser — **released**;
- dependency-neutral Dataset — **released**;
- Dataset Contracts — **released**.

The complete stabilization rationale and guardrails are documented under `docs/architecture/foundation-stabilization-v0.1xx.md`.

## V0.2.0 — complete acquisition reference slice

The stable release connects the V0.2 layers into installable, executable reference jobs:

```text
demo.http_csv
HttpSource -> Retry -> RAW -> CsvParser -> Dataset -> DatasetContract -> Validation

demo.http_json
HttpSource -> Retry -> RAW -> JsonParser -> Dataset -> DatasetContract -> Validation
```

Together with the Foundation demo, the expected installed job set is:

```text
demo.local_file
demo.http_csv
demo.http_json
```

Run the HTTP slices deterministically without network access:

```bash
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
```

The fixture transport is confined to the demo package. Production job code can pass a real `url` without fixture mode and uses `HttpxClient` through `HttpSource`.

A `ValidationResult` returned by a step is now written to the manifest, indexed in MetadataStore, and announced through `VALIDATION_COMPLETED`. ERROR issues fail the run after evidence is persisted; warnings/review issues remain non-fatal.

For a fresh development environment, upgrade packaging tooling before the security gate so `pip-audit` does not report vulnerabilities in an outdated `pip` executable itself:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## V0.2.0 release artifacts

The official release is validated as three complementary artifact families:

```text
pyingestkit-v0.2.0.zip
dist/pyingestkit-0.2.0.tar.gz
dist/pyingestkit-0.2.0-py3-none-any.whl
examples/plugin_package/dist/pyingestkit_demo_jobs-0.2.0.tar.gz
examples/plugin_package/dist/pyingestkit_demo_jobs-0.2.0-py3-none-any.whl
pyingestkit-v0.2.0-validation-evidence.zip
```

The source ZIP excludes virtual environments, runtime workspaces, caches, build outputs, generated distributions, bytecode and egg-info directories. The validation-evidence ZIP contains command outputs and SHA-256 checksums, not source code.
