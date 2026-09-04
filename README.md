# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release: v0.4.0](https://img.shields.io/badge/release-v0.4.0--stable-success.svg)](CHANGELOG.md)

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

This source repository contains **V0.4.0 — Diff / Replay / Versioning Release**, built on the frozen V0.3.0 Quality & Formats baseline.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed DAG scheduler, a Data Platform, a Data Catalog, an IAM platform, an AI/agent framework, or a warehouse target framework.

The stable V0.4 doctrine is explicit:

```text
Diff              != Transformation
Versioning        != Git for data
Replay            != Scheduler retry
PublishedDataset  != last file written
DatasetVersion    != package SemVer
Snapshot          != pickle
Replay            != new source acquisition
PyIngestKit       != orchestrator
```

## V0.4.0 stable baseline

V0.4.0 retains the V0.1-V0.3 foundation and adds the following stable surfaces:

- **Dataset fingerprints** — deterministic, type-aware SHA-256 identities distinct from RAW byte hashes;
- **Dataset diff** — keyed comparison when logical identity exists, exact multiset semantics otherwise, bounded deterministic entries, schema diff, and opt-in value capture;
- **Portable diff evidence** — `reports/diff.json` with runtime events, manifest references, and additive metadata persistence;
- **Dataset snapshots** — versioned typed JSON with deterministic round-trip semantics and no pickle;
- **Dataset version registry** — immutable content-addressed `DatasetVersion` history;
- **PublishedDataset** — atomic pointer to the currently published version;
- **Replay from RAW** — a new run reconstructed from historical immutable RAW without re-contacting the original source;
- **Replay lineage and verification** — source-run lineage plus strict Dataset fingerprint comparison when the original execution is verifiable;
- **CLI inspection** — `versions`, `published`, and `replay` extend the existing `jobs`, `inspect`, `run`, `runs`, and `status` commands;
- **Seven executable reference jobs** — the six V0.3 jobs plus `demo.versioned_ndjson` proving the V0.4 vertical slice.

Stable serialization/report contracts are frozen at:

```text
Dataset fingerprint canonical codec  = 1
Dataset snapshot_version              = "1"
Diff report_version                   = "1"
```

An incompatible future format change must use a new explicit version rather than silently reinterpret V0.4 artifacts.

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

A decorated job compiles to the same imperative `Job`/`Pipeline` model used by `Runner`. Direct unit testing remains explicit through `step_definition.fn(...)`.

The decorator API is a deterministic sequential pipeline builder, not a distributed DAG engine. Parallel workers, sensors, scheduling, generic branching and cluster orchestration remain out of scope.

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

## CLI execution

```bash
pyingest --version
pyingest --help

# Discovery
pyingest jobs
pyingest inspect demo.local_file
pyingest inspect demo.versioned_ndjson

# V0.1-V0.3 reference jobs
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.excel_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.parquet_quality --config examples/plugin_package/demo-quality.yml

# V0.4 versioned reference slice
pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=1
pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=2

# Version / publication inspection
pyingest versions demo.versioned_ndjson --workspace .pyingest
pyingest published demo.versioned_ndjson --workspace .pyingest

# Historical RAW replay
pyingest replay <run-id> --config examples/plugin_package/demo-versioned.yml

# History and status
pyingest runs
pyingest status <run-id-or-prefix>
```

Machine-readable modes are available through `--json` on the relevant commands. Operational logs are written to stderr.

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
│       │   ├── profile.json
│       │   └── diff.json
│       └── manifest.json
├── versions/
│   └── <dataset-id>/
│       └── <content-addressed-version>/
│           ├── version.json
│           └── snapshot.json
└── published/
    └── <dataset-id>.json
```

A plugin does not silently select its own global workspace. Alternative workspaces are explicit runtime configuration.

## ArtifactStore vs MetadataStore

```text
ArtifactStore                         MetadataStore
─────────────                         ─────────────
RAW payloads                          runs
staging/candidate files               steps
validation/profile/diff reports       artifact metadata
manifests                             validations
dataset version snapshots             diff summaries
published dataset pointers            version/publication metadata
                                      runtime events / replay lineage
```

The manifest remains the portable run snapshot. MetadataStore is the queryable historical index. Neither replaces the other.

## Quality, Diff, Versioning and Replay

The V0.4 path builds directly on the materialized `Dataset` contract:

```text
External Source
      ↓
Immutable RAW
      ↓
Parser
      ↓
Dataset
      ├──► Validate / Profile
      ├──► Fingerprint
      ├──► Diff against PublishedDataset
      ├──► Snapshot / DatasetVersion
      └──► Publish atomically

Historical RAW
      ↓
Replay resolver
      ↓
new Run
      ↓
Dataset fingerprint verification
```

Example fingerprint/diff use:

```python
from pyingestkit import Dataset, DatasetDiffer, DatasetFingerprinter, DiffPolicy

before = Dataset([{"id": 1, "name": "Alice"}], fields=("id", "name"))
after = Dataset([{"id": 1, "name": "Alicia"}], fields=("id", "name"))

fingerprint = DatasetFingerprinter().fingerprint(after)
diff = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(before, after)
```

Replay is intentionally strict: it reuses historical RAW. It is not allowed to fall back silently to a live HTTP/file acquisition when the expected historical artifact cannot be resolved.

## Database backends

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

Secrets are referenced by environment variable name, not embedded in versioned YAML. V0.4 schema evolution remains additive for built-in SQLite/PostgreSQL stores; optional capabilities preserve compatibility with custom MetadataStore implementations.

## Logging convention

Terminal output follows the stable human convention:

```text
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.versioned_ndjson] Run started
2026-09-04 09:19:38  INFO     [run=086b2f62 job=demo.versioned_ndjson step=FetchVersionedNdjson] Step started
```

Terminal timestamps use local time; JSON logs and metadata keep timezone-aware ISO-8601 timestamps and full run UUIDs. Common secret patterns and secret-looking runtime parameter keys are redacted. DEBUG details are emitted only when verbose/debug logging is enabled.

## Quality and release gates

```bash
make test
make quality
make security
make build
make verify
make release-check
```

- `make quality`: Ruff linting, Ruff formatting and Mypy strict type checking;
- `make security`: Bandit static analysis and `pip-audit` dependency vulnerability checks;
- `make verify`: functional/contract tests, public API freeze, quality, security and package builds;
- `make release-check`: `make verify` plus isolated clean-wheel smoke validation with Excel/Parquet extras and all seven reference jobs.

The GitHub CI matrix validates Python **3.11, 3.12 and 3.13**. The Security workflow is a separate required qualification signal.

## V0.4.0 stable reference suite

```text
demo.local_file        : Local file -> immutable RAW
demo.http_csv          : HTTP -> RAW -> CSV -> Dataset -> Contract V2
demo.http_json         : HTTP -> RAW -> JSON -> Dataset -> Contract V2
demo.ndjson_quality    : NDJSON -> Dataset -> Contract V2 -> Profile -> reports
demo.excel_quality     : XLSX/OpenPyXL -> Dataset -> Contract V2 -> Profile -> reports
demo.parquet_quality   : Parquet/PyArrow -> Dataset -> Contract V2 -> Profile -> reports
demo.versioned_ndjson  : V1 -> V2 -> diff -> version -> publish -> strict RAW replay
```

The versioned reference job deliberately proves one added, one removed, one changed and one unchanged row between V1 and V2, then replays V2 from historical RAW with fingerprint equality.

## Release artifacts

```text
dist/pyingestkit-0.4.0.tar.gz
dist/pyingestkit-0.4.0-py3-none-any.whl
examples/plugin_package/dist/pyingestkit_demo_jobs-0.4.0.tar.gz
examples/plugin_package/dist/pyingestkit_demo_jobs-0.4.0-py3-none-any.whl
pyingestkit-v0.4.0.zip
```

See [`docs/guides/release-validation-v0.4.0.md`](docs/guides/release-validation-v0.4.0.md) for the stable validation procedure.

## Status and roadmap

**V0.4.0 is the stable Diff / Replay / Versioning release.**

- **V0.1.x Foundation** — frozen;
- **V0.2.0 Acquisition** — frozen;
- **V0.3.0 Quality & Formats** — frozen;
- **V0.4.0 Diff / Replay / Versioning** — stable release;
- later target/load capabilities remain outside the V0.4 scope.
