# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release: v0.3.0](https://img.shields.io/badge/release-v0.3.0--stable-success.svg)](CHANGELOG.md)

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

This source repository contains **V0.3.0 — Quality & Formats Release**, built on the officially sealed V0.2.0 Acquisition Release and the validated V0.1.x Foundation baseline.


## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed DAG scheduler, a Data Platform, a Data Catalog, an IAM platform, or an AI/agent framework.


## V0.3.0 Quality & Formats baseline

- **Declarative & Imperative APIs**: `@job` / `@step` decorators and `Job` / `Step` / `Pipeline` models compiled to a single execution runtime (`Runner`);
- **Formats & Parsers**:
  - `CsvParser` & `JsonParser` (Core);
  - `NdjsonParser` (Core structural parser);
  - `ExcelParser` (via optional `openpyxl` extra);
  - `ParquetParser` (via optional `pyarrow` extra);
- **Dataset Contracts V2**: `FieldContract` and `DatasetContract` with `pattern`, `allowed_values`, `min/max_value`, `min/max_length`, `unique_together`, logical `primary_key`, and bounded `ValidationIssue` collection;
- **Dataset Profiling**: Structural and descriptive `DatasetProfiler` generating deterministic `DatasetProfile` metadata;
- **Portable Quality Reports**: `reports/validation.json` and `reports/profile.json` artifacts linked to manifests and emitted via runtime events;
- **HTTP Acquisition & Provenance**: Framework-owned `HttpSource` / `HttpxClient` with conservative `RetryPolicy` and secret-redacted HTTP provenance;
- **CLI Tooling**: `pyingest` CLI (`jobs`, `inspect`, `run`, `runs`, `status`) with `-v/--verbose`, `-q/--quiet`, and `--json` machine-readable output;
- **Unified Workspace**: `.pyingest/` layout (`state/`, `logs/`, `runs/`, `published/`) with SQLite default and PostgreSQL optional adapter (`pyingestkit[postgres]`);
- **Immutability & Traceability**: Immutable RAW payloads with SHA-256 hashes, manifest generation, and structured logging.


## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,excel,parquet]"
```

Install the bundled reference demo job pack:

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


## CLI Execution

```bash
pyingest --version
pyingest --help

# List and inspect registered jobs
pyingest jobs
pyingest inspect demo.local_file
pyingest inspect demo.http_csv
pyingest inspect demo.http_json
pyingest inspect demo.excel_quality
pyingest inspect demo.ndjson_quality
pyingest inspect demo.parquet_quality

# Run standard reference jobs
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.excel_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.parquet_quality --config examples/plugin_package/demo-quality.yml

# History and status inspection
pyingest runs
pyingest status <run-id-or-prefix>
```

Verbose / quiet execution:

```bash
pyingest run demo.local_file -v --param path=examples/plugin_package/data/sample.txt
pyingest run demo.local_file -q --param path=examples/plugin_package/data/sample.txt
```

Machine-readable output on stdout:

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
│       │   ├── validation.json
│       │   └── profile.json
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
reports (validation/profile)          artifact metadata
manifests                             validations
published datasets                    publications
                                      runtime events
```

The manifest remains the portable run snapshot. MetadataStore is the queryable historical index. Neither replaces the other.


## Quality Contracts V2 & Dataset Profiling

```text
Dataset ──► DatasetProfiler ──► DatasetProfile
   │                              │
   └────► DatasetContract V2      └────► reports/profile.json
              │
              └────────────────────────► reports/validation.json
                                         │
                                         ├── manifest report references
                                         └── runtime events
```

```python
from pyingestkit import CsvParser, DatasetContract, FieldContract, DatasetProfiler

dataset = CsvParser().parse(raw_artifact)
result = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=str, unique=True),
        FieldContract("name", nullable=False, expected_type=str),
    ),
    allow_extra_fields=False,
    min_rows=1,
).validate(dataset)

profile = DatasetProfiler().profile(dataset)
```

The boundary is explicit: `Parser != business normalizer`, and `DatasetContract` validates without mutating the dataset.


## Database Backends

### SQLite default

```yaml
metadata:
  backend: sqlite
```

By default the database is resolved relative to the effective workspace: `.pyingest/state/pyingest.sqlite3`.

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
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality] Run started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=FetchExcelFixture] Step started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=FetchExcelFixture] Step succeeded 0.054s
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ParseExcel] Step started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ParseExcel] Step succeeded 0.004s
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ValidateExcelDataset] Step started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ValidateExcelDataset] Step succeeded 0.006s
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ProfileExcelDataset] Step started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality step=ProfileExcelDataset] Step succeeded 0.009s
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.excel_quality] Run succeeded 0.105s
```

Terminal timestamps use local time; JSON logs and metadata keep timezone-aware ISO-8601 timestamps and full run UUIDs. Common secret patterns and secret-looking runtime parameter keys are redacted.


## Quality gates

```bash
make test
make quality
make security
make build
make verify
make release-check
```

- `make quality`: Enforces Ruff linting, Ruff formatting, and Mypy strict type checking.
- `make security`: Enforces Bandit static security scanning and `pip-audit` dependency vulnerability checks.
- `make verify`: Complete source gate running functional tests, public API checks, quality, security, and package builds.
- `make release-check`: Executes `make verify` plus an isolated fresh virtualenv wheel smoke test over all six reference jobs with optional extras installed.


## V0.3.0 Release Reference Suite

The V0.3.0 release is validated through six executable reference jobs:

```text
demo.local_file       : Local file -> RAW storage
demo.http_csv         : HTTP -> RAW -> CsvParser -> Dataset -> Contract V2 -> Validation
demo.http_json        : HTTP -> RAW -> JsonParser -> Dataset -> Contract V2 -> Validation
demo.ndjson_quality   : NDJSON -> Dataset -> Contract V2 -> Profile -> Quality reports
demo.excel_quality    : XLSX (openpyxl) -> Dataset -> Contract V2 -> Profile -> Quality reports
demo.parquet_quality  : Parquet (pyarrow) -> Dataset -> Contract V2 -> Profile -> Quality reports
```


## Release Artifacts

```text
dist/pyingestkit-0.3.0.tar.gz
dist/pyingestkit-0.3.0-py3-none-any.whl
examples/plugin_package/dist/pyingestkit_demo_jobs-0.3.0.tar.gz
examples/plugin_package/dist/pyingestkit_demo_jobs-0.3.0-py3-none-any.whl
```


## Status & Roadmap

V0.3.0 is the stable **Quality & Formats** milestone. The release freezes Contracts V2, profiling, portable quality reports, NDJSON, Excel and Parquet adapters, and the six reference jobs.

- **V0.1.x Baseline**: Foundation & Core Pipeline (Frozen)
- **V0.2.0 Acquisition**: HTTP Source, Retry Policy, RAW Provenance (Frozen)
- **V0.3.0 Quality & Formats**: Contracts V2, Profiling, Quality Reports, NDJSON, XLSX, Parquet (Stable Release)
- **V0.4.0 (Upcoming)**: Dataset Diff, Replay & Versioning
