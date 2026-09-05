# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release: v0.6.0](https://img.shields.io/badge/release-v0.6.0--stable-success.svg)](CHANGELOG.md)

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

V0.6.0 extends the V0.5 PostgreSQL persistence baseline with durable S3-compatible artifacts, remote dataset versions/publication, and strict cross-host replay.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed scheduler, a Data Platform, a Data Catalog, an IAM platform, or a cloud-provisioning framework.

```text
ArtifactStore       != Target
ArtifactStore       != MetadataStore
DatasetVersionStore != ArtifactStore
S3-compatible       != AWS-only
DatasetVersion      != S3 object version
Replay              != new source acquisition
PyIngestKit         != orchestrator
```

## V0.6.0 stable capabilities

- immutable RAW with SHA-256 provenance;
- CSV, JSON, NDJSON, Excel and Parquet parsing behind a dependency-neutral `Dataset`;
- contracts, validation, profiling and portable quality reports;
- deterministic Dataset fingerprints and diff reports;
- immutable content-addressed DatasetVersion snapshots and PublishedDataset pointers;
- strict replay from historical RAW;
- transactional PostgreSQL target loads with COPY and idempotency;
- `ArtifactURI` and `StoredArtifact` portable durable references;
- optional `S3ArtifactStore` for RAW/reports/manifests;
- optional `S3DatasetVersionStore` for remote snapshots/publication;
- MinIO-tested S3-compatible behavior;
- full replay from a fresh host/workspace using shared PostgreSQL metadata + object storage;
- nine executable reference jobs.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,excel,parquet,postgres,s3]"
python -m pip install -e examples/plugin_package
```

Production consumers can select only the required extras:

```bash
pip install "pyingestkit[s3]"
pip install "pyingestkit[postgres]"
```

## Minimal S3-compatible configuration

```yaml
runtime:
  workspace: .pyingest

artifacts:
  backend: s3
  s3:
    bucket: my-pyingest-artifacts
    prefix: pyingest
    region_name: eu-west-3
    endpoint_url_env: PYINGEST_S3_ENDPOINT_URL
    cache_path: .pyingest
```

Credentials use the boto3/AWS provider chain and are not stored in YAML.

For MinIO:

```bash
export PYINGEST_S3_ENDPOINT_URL='https://minio.example.internal'
```

## API

Decorator style:

```python
from pyingestkit import RunContext, job, step

@step(name="Fetch")
def fetch(context: RunContext):
    ...

@step
def normalize(data):
    ...

@job(id="public.postal_codes", version="1.0.0")
def postal_codes() -> None:
    fetch()
    normalize()
```

Imperative style:

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
pyingest jobs
pyingest inspect demo.versioned_s3
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest versions demo.versioned_s3 --config examples/plugin_package/demo-versioned-s3.yml
pyingest published demo.versioned_s3 --config examples/plugin_package/demo-versioned-s3.yml
pyingest replay <run-id> --config examples/plugin_package/demo-versioned-s3.yml
pyingest runs
pyingest status <run-id-or-prefix>
```

## V0.6 reference jobs

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
demo.versioned_ndjson
demo.versioned_postgres
demo.versioned_s3
```

`demo.versioned_s3` is the full V0.6 vertical slice: V1 → V2 → remote RAW/reports/snapshots → PostgreSQL → publish V2 → destroy workspace A → strict replay from workspace B → fingerprint match → idempotent target SKIP.

## Durable storage model

```text
PostgreSQL metadata
  └── runs / artifact locations / lineage / target loads

S3-compatible object storage
  └── RAW / reports / manifests / DatasetVersion snapshots / PublishedDataset pointer

PostgreSQL Target
  └── consumable dataset
```

The durable artifact URI is independent from a local parser-facing cache path.

## Quality and release gates

```bash
make test
make quality
make security
make build
make verify
make release-check
```

GitHub CI qualifies Python 3.11/3.12/3.13, PostgreSQL 16, MinIO/S3 integration, full cross-host object-storage replay, public API freeze, build, and isolated clean-wheel installation.

See:
- `docs/architecture/object-storage-release-v0.6.0.md`
- `docs/guides/configure-object-storage.md`
- `docs/guides/release-validation-v0.6.0.md`
- `SECURITY.md`

## Release artifacts

```text
pyingestkit-0.6.0-py3-none-any.whl
pyingestkit-0.6.0.tar.gz
pyingestkit_demo_jobs-0.6.0-py3-none-any.whl
pyingestkit_demo_jobs-0.6.0.tar.gz
pyingestkit-v0.6.0.zip
SHA256SUMS
```
