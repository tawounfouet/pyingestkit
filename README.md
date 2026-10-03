# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stable: 2.0.0](https://img.shields.io/badge/stable-2.0.0-brightgreen.svg)](docs/releases/v2.0.0.md)

**PyIngestKit** is a focused Python framework for reliable, traceable and replayable ingestion.

> Acquire external data, preserve durable RAW evidence, decode and validate it, create immutable dataset versions, then publish or materialize them explicitly.

## 2.0 stable

`2.0.0` is the LOT-22 stable release of the clean-slate V2 architecture. It promotes the fully qualified RC contract without changing the frozen public root, runtime signature, provider Protocols or boundary wire versions.

The V1 `Job / Pipeline / Step / Runner` execution model is **not** aliased into the 2.0 root. Existing V1 workloads should remain pinned to the 1.x line until they are migrated semantically.

## 2.1 development line

Repository `main` is now on **2.1.0a4 / LOT-26**. LOT-23 established provider-neutral governance contracts, LOT-24 added durable Memory/PostgreSQL lifecycle ledgers, LOT-25 added filesystem CAS, and LOT-26 adds endpoint-qualified S3 conditional publication with provider-enforced cross-client compare-and-swap. The exact 2.0 package root and LOT-23 Protocols remain frozen.

Retention/holds/guarded GC, governed rollback and full RC conformance remain sequenced in LOT-27 through LOT-30.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed scheduler, a Data Platform, a Data Catalog, IAM, or cloud provisioning.

```text
ArtifactStore       != DatasetVersionStore
ArtifactStore       != publication target
DatasetVersion      != provider object version
Replay              != new source acquisition
PyIngestKit         != orchestrator
```

## Canonical 2.0 API

The 2.0 root is intentionally small:

```python
from pyingestkit import (
    ArtifactReference,
    DatasetVersion,
    DatasetVersionReference,
    IngestionDefinition,
    IngestionResult,
    IngestionRun,
    IngestionRunId,
    IngestionRuntime,
    PublishedDataset,
    ResourceReference,
    Source,
)
```

The canonical synchronous execution entry point is `IngestionRuntime.run(...)`.

```python
from pathlib import Path

from pyingestkit import IngestionDefinition, IngestionRuntime, Source
from pyingestkit.adapters.filesystem import FileArtifactStore, FileSourceConnector
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.decoders import CsvDecoder
from pyingestkit.stores import FileDatasetVersionStore

root = Path("./.pyingest-v2")

sources = SourceRegistry([FileSourceConnector()])
decoders = DecoderRegistry([CsvDecoder()])

runtime = IngestionRuntime(
    sources=sources,
    decoders=decoders,
    artifacts=FileArtifactStore(root=root / "artifacts"),
    versions=FileDatasetVersionStore(root=root / "datasets"),
)

definition = IngestionDefinition(
    name="customers",
    source=Source.file(path="./customers.csv"),
    decoder="csv",
    dataset="customers",
)

result = runtime.run(definition)
print(result.status)
```

## Installation

Base installation is provider-neutral:

```bash
pip install "pyingestkit==2.0.0"
```

Install only the providers required by the application:

```bash
pip install "pyingestkit[http]==2.0.0"
pip install "pyingestkit[postgres]==2.0.0"
pip install "pyingestkit[s3]==2.0.0"
pip install "pyingestkit[excel]==2.0.0"
pip install "pyingestkit[parquet]==2.0.0"
```

The base package does not require `httpx`, SQLAlchemy, psycopg, boto3, OpenPyXL, PyArrow or PyTransformKit.

## Core lifecycle

```text
Source
  ↓
acquisition
  ↓
durable RAW ArtifactReference
  ↓
decoder
  ↓
validation / quality evidence
  ↓
immutable DatasetVersion
  ↓
DatasetVersionReference
  ├── explicit publication
  ├── explicit target materialization
  └── strict replay / verification
```

## Providers and ports

The stable provider boundary is expressed through framework-owned Protocols:

```text
SourceConnector
Decoder
ArtifactStore
DatasetVersionStore
DatasetPublisher
DatasetVersionMaterializerV2
DatasetTargetV2
```

Provider implementations remain replaceable. The framework does not expose boto3 clients, SQLAlchemy engines, open file handles or DataFrames as durable public contracts.

## Replay and reproducibility

V2 replay starts from preserved evidence. It allocates a new `IngestionRunId`, resolves the historical RAW artifact and verifies the resulting immutable dataset identity.

Replay is fail-closed when required historical evidence is missing or inconsistent. It does not silently reacquire the original source.

## PyTransformKit integration

Transformation remains outside the ingestion core and is integrated through portable references under:

```text
pyingestkit.integrations.pytransformkit
```

The qualified Customer 360 path is:

```text
PyIngestKit DatasetVersionReference
  ↓
portable ResourceReference
  ↓
PyTransformKit InputBinding
  ↓
transformation result resource
  ↓
PyIngestKit governed DatasetVersion
  ↓
publication
```

PyTransformKit remains optional; stable qualification installs the explicitly validated 1.1.0 implementation used by the integration tests.

## Migration from 1.x

PyIngestKit 2.0 is a major-version boundary, not an alias release.

V1 root names such as `Job`, `Pipeline`, `Step`, `Runner`, `RunContext`, `job` and `step` are not part of the 2.0 root contract.

Migration tooling lives under:

```python
import pyingestkit.migration
```

It converts supported persisted semantics and produces explicit migration decisions without executing V1 plugins or silently loading secrets.

See [Migrating PyIngestKit 1.x applications to 2.0](docs/guides/migrate-v1-to-v2.md).

## Qualified matrix

LOT-22 requalifies the unchanged RC contract across:

- Python 3.11, 3.12, 3.13 and 3.14;
- clean wheel and source-distribution installs;
- provider-neutral base installation;
- filesystem acquisition/artifacts/version storage;
- HTTP acquisition;
- PostgreSQL target materialization;
- S3-compatible object storage and cross-host replay;
- canonical serialization and migration fixtures;
- publication reconciliation / outcome-uncertainty paths;
- PyTransformKit integration;
- Customer 360 built-artifact E2E;
- Ruff, formatting, mypy, Bandit and `pip-audit`;
- sealed V1.0.0 historical evidence on the immutable V1 tag.

## Quality and release gates

```bash
make check-v2
make quality
make security
make build
make release-check
python scripts/check_v2_stable.py
```

The terminal CI gate is `stable-release-gate`, which is release-blocking for `2.0.0`.

## Stable compatibility policy

The 2.0 root, stable provider Protocols and version-1 boundary wire contracts are the compatibility baseline for the 2.x line. Breaking changes require a new major version; additive evolution must preserve these frozen contracts.

See:

- [2.0.0 stable release notes](docs/releases/v2.0.0.md)
- [2.0 provider compatibility matrix](docs/reference/provider-compatibility-v2.md)
- [2.0 stable qualification](docs/releases/v2.0.0-qualification.md)
- [V1 → V2 migration guide](docs/guides/migrate-v1-to-v2.md)
- [LOT-20 Customer 360 beta gate](docs/architecture/v2-lot20-customer360-beta-gate.md)
- [LOT-18 semantic migration](docs/architecture/v2-lot18-v1-semantic-migration.md)
- [Security policy](SECURITY.md)

## V1 historical line

The immutable V1 stable line remains available through tag `v1.0.0`. Its CLI, demo jobs and Job/Pipeline/Step execution semantics are historical 1.x contracts and are intentionally separate from the 2.0 public API.
