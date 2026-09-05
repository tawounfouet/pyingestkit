# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stable: v1.0.0](https://img.shields.io/badge/stable-v1.0.0-brightgreen.svg)](docs/releases/v1.0.0.md)

**PyIngestKit** is a focused Python framework for reliable, traceable batch ingestion.

> Transform an external source into a reliable, validated, reproducible and publishable dataset without rewriting ingestion plumbing for every job.

**V1.0.0 Stable** is the first protected 1.x framework contract. It promotes the qualified RC1
baseline without adding product scope and retains the immutable `v0.6.0` release as executable
historical upgrade evidence. The annotated `v1.0.0` release tag is created only after the exact stable
merge SHA passes post-merge CI and Security.

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

## V1.0.0 stable capabilities

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
- deterministic plugin/config/error/CLI/logging behavior governed for 1.x;
- explicit stable Python/public/persisted compatibility contracts;
- five representative pilots covering nine executable reference jobs;
- clean-wheel packaging plus an executable V0.6.0 -> 1.0.0 upgrade smoke.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,excel,parquet,postgres,s3]"
python -m pip install -e examples/plugin_package
```

Production consumers can select only the required extras:

```bash
pip install "pyingestkit[s3]>=1,<2"
pip install "pyingestkit[postgres]>=1,<2"
```

Stable qualification builds and installs the generated `1.0.0` wheels in clean environments before
the immutable release tag is published.

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

## Configuration Management & Backend Requirements

PyIngestKit resolves configuration in the following order:
1. Explicit `--config <path.yml>` CLI flag.
2. `PYINGEST_CONFIG` environment variable path.
3. `PYINGEST_ENV=<env>` selecting `pyingest.yml.<env>`.
4. Automatic discovery of `pyingest.yml`, `pyingestkit.yml`, or `.pyingest.yml` in the working directory.
5. Local in-memory defaults (`filesystem` artifacts & `sqlite` metadata).

Explicit environment/profile selectors are fail closed: a missing selected config is an error.
Workspace precedence is `--workspace` → `PYINGEST_WORKSPACE` → `runtime.workspace` → `.pyingest`.

Jobs can explicitly declare backend requirements (e.g. `requires_artifacts="s3"`, `requires_metadata="postgres"`). If a job's requirements are not met by the active configuration, `pyingest run` halts before executing any step with a clear error message.

### Configuration Profiles & Environment Files

Three ready-to-use YAML profiles and corresponding environment templates in `envs/` are provided.
The `*.example` dotenv files are templates only and are never auto-loaded.

- `pyingest.yml.dev` & `envs/.env.dev.example`: local filesystem artifacts + SQLite metadata.
- `pyingest.yml.stg` & `envs/.env.stg.example`: S3-compatible artifacts via MinIO + PostgreSQL metadata.
- `pyingest.yml.prod` & `envs/.env.prod.example`: S3-compatible artifacts via AWS S3 / Cloudflare R2 + PostgreSQL metadata.

```bash
cp envs/.env.dev.example .env
cp pyingest.yml.dev pyingest.yml
```

### Project auto-discovery

```bash
pyingest --version
pyingest config
pyingest jobs
pyingest inspect demo.versioned_s3

pyingest run demo.local_file --param path=examples/plugin_package/data/sample.txt
pyingest run demo.http_csv
pyingest run demo.http_json
pyingest run demo.ndjson_quality
pyingest run demo.excel_quality
pyingest run demo.parquet_quality

pyingest run demo.versioned_postgres --param revision=1
pyingest run demo.versioned_s3 --param revision=1
pyingest run demo.versioned_s3 --param revision=2

pyingest versions demo.versioned_s3
pyingest published demo.versioned_s3
pyingest runs
pyingest status
pyingest replay
```

### Explicit demo configuration

```bash
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.excel_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.parquet_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.versioned_ndjson --config examples/plugin_package/demo-versioned.yml --param revision=1
pyingest run demo.versioned_postgres --config examples/plugin_package/demo-versioned-postgres.yml --param revision=1
pyingest run demo.versioned_s3 --config examples/plugin_package/demo-versioned-s3.yml --param revision=1
pyingest run demo.versioned_s3 --config examples/plugin_package/demo-versioned-s3.yml --param revision=2
```

## V1 stable reference jobs

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

`demo.versioned_s3` remains the full cross-host vertical slice: V1 → V2 → remote RAW/reports/snapshots → PostgreSQL → publish V2 → destroy workspace A → strict replay from workspace B → fingerprint match → idempotent target SKIP.

## Durable storage model

```text
PostgreSQL metadata
  └── runs / artifact locations / lineage / target loads

S3-compatible object storage
  └── RAW / reports / manifests / DatasetVersion snapshots / PublishedDataset pointer

PostgreSQL Target
  └── consumable dataset
```

## Quality and release gates

```bash
make test
make quality
make security
make build
make check
make release-check
```

GitHub CI qualifies Python 3.11/3.12/3.13, PostgreSQL 16, MinIO/S3 integration, full cross-host
object-storage replay, A1/A2/B1/B2 governance, historical RC1 evidence, the stable release contract,
clean-wheel installation and the real `v0.6.0` → `1.0.0` upgrade path.

See:
- `docs/guides/v1-quickstart.md`
- `docs/guides/v1-production-pilot.md`
- `docs/guides/migrate-v0.6-to-v1.md`
- `docs/guides/release-validation-v1.0.0.md`
- `docs/reference/stable-contract-v1.md`
- `docs/reference/public-api.md`
- `docs/reference/compatibility-v1.md`
- `docs/reference/stability-v1.md`
- `docs/reference/pilots-v1.md`
- `SECURITY.md`

## V1.0.0 stable build artifacts

```text
pyingestkit-1.0.0-py3-none-any.whl
pyingestkit-1.0.0.tar.gz
pyingestkit_demo_jobs-1.0.0-py3-none-any.whl
pyingestkit_demo_jobs-1.0.0.tar.gz
SHA256SUMS
```

CI groups these as `pyingestkit-v1.0.0-source` and `pyingestkit-v1.0.0-dist`. The historical `v0.6.0`
and RC1 evidence remain immutable and separate. The annotated `v1.0.0` tag is created only after the
exact stable merge SHA passes post-merge CI and Security.
