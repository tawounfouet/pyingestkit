# PyIngestKit V1 — Product Scope Freeze

Status: **V1.0.0-a1 — Scope Freeze**

PyIngestKit V1 keeps the original product boundary:

> **PyIngestKit owns HOW TO INGEST. External orchestrators own WHEN TO RUN.**

The V1 scope is deliberately narrower than a data platform. Stability is measured by the quality
of the retained contracts, not by the number of providers or adjacent platform features.

## 1. IN SCOPE

The V1 core product covers:

```text
job discovery
runtime execution
acquisition
RAW persistence
parsing
normalization hooks
validation
profiling
fingerprinting
diff
versioning
publication
replay
metadata
persistence targets
CLI
plugins
configuration
observability
```

Because V0.6 was justified, implemented, released and qualified, V1 also includes the existing
S3-compatible object-storage contract:

```text
ArtifactURI / StoredArtifact
ArtifactStore location independence
S3ArtifactStore
S3DatasetVersionStore
remote immutable RAW
remote reports/manifests
remote immutable dataset versions
published pointer
cross-host replay
```

This is a **single stable protocol family** (S3-compatible), not a promise to implement every cloud
storage provider.

## 2. EXTENSION-ONLY

The following are supported product capabilities but remain optional integrations rather than
mandatory core-runtime dependencies:

```text
PostgreSQL target + PostgreSQL metadata
S3-compatible object storage
Excel parsing
Parquet parsing
external job packs / plugins
```

They are selected through package extras and extension contracts. A basic local installation must
remain useful without cloud SDKs or a running PostgreSQL service.

## 3. OUT OF SCOPE

V1 explicitly does not become any of the following:

```text
scheduler
DAG orchestration platform
worker fleet
queue system
cluster manager
IAM / RBAC platform
data catalog
external lineage platform
GUI
SaaS
ML / AI platform
stream processor
```

Concrete examples that remain out of product scope include Airflow/Prefect/Dagster-style scheduling,
Celery-style distributed workers, Kafka/Spark streaming/distributed runtimes, web administration
surfaces and organization-wide IAM/catalog responsibilities.

## 4. FUTURE / NOT COMMITTED

Interesting ideas do not become roadmap commitments merely because they are technically possible.
In particular, V1 makes no commitment to:

```text
Azure Blob adapter
GCS adapter
provider-specific cloud provisioning
bucket lifecycle/replication management
distributed execution engine
new orchestration engine
data catalog / RBAC / GUI features
AI agents / RAG / ML workflows
streaming ingestion engine
```

Any future proposal must pass a scope review before it can enter a later roadmap.

## 5. Architectural boundaries

The retained V1 boundaries are:

```text
ArtifactStore       != Target
ArtifactStore       != MetadataStore
DatasetVersionStore != ArtifactStore
DatasetVersion      != provider object version
PublishedDataset    != PostgreSQL table
Metadata DB         != Target DB
Replay              != new source acquisition
PyIngestKit         != orchestrator
```

Storage, metadata and targets have separate responsibilities:

```text
external source
      ↓
acquisition
      ↓
immutable RAW ──────────────── ArtifactStore
      ↓
parse / normalize / validate
      ↓
Dataset
      ├── fingerprint / diff / version / publish
      ├── metadata records ─── MetadataStore
      └── durable load ─────── Target
```

## 6. Dependency direction

Expected direction:

```text
core contracts
      ↑
framework implementations
      ↑
optional integrations / provider SDKs
```

Forbidden direction:

```text
core
  ↓
PostgresTarget implementation / psycopg
  ↓
S3ArtifactStore implementation / boto3
```

The runtime may depend on framework contracts and neutral runtime models. It must not acquire a
hard dependency on optional provider SDKs.

## 7. Dependency governance

V1 does not adopt a zero-third-party-dependency doctrine. Established production-grade Python
libraries are acceptable when they have a clear responsibility, bounded version constraints and
security/quality governance.

Base runtime families currently retained:

```text
Typer / Rich
Pydantic / PyYAML
SQLAlchemy
httpx
tenacity
python-dotenv
```

Provider-heavy capabilities remain optional extras where appropriate.

## 8. Optional-extra scope

The retained extra names are:

```text
dev
excel
parquet
postgres
s3
```

Responsibilities are intentionally narrow:

- `excel`: Excel parsing adapter;
- `parquet`: Parquet parsing adapter;
- `postgres`: PostgreSQL driver/integration support;
- `s3`: S3-compatible SDK support;
- `dev`: test, quality, security and release tooling.

Adding or repurposing an extra is a public packaging decision and requires an explicit scope review.

## 9. Python support scope

The V1 candidate matrix is:

```text
Python 3.11
Python 3.12
Python 3.13
```

Support is defined jointly by package metadata, contract tests and CI. A future support change must
be deliberate and documented.

## 10. Architectural fitness gates

A1 introduces tests that protect these boundaries:

```text
core must not import optional provider implementations
core must not import boto3/psycopg directly
local/base install must not require boto3/psycopg/openpyxl/pyarrow
runtime runner must not depend on PostgresTarget/S3ArtifactStore
orchestration-platform dependencies must stay out of core packaging
```

The tests do not replace architectural review; they make high-value scope violations mechanically
visible.

## 11. Change-admission rule for V1 stabilization

During the V1 stabilization sequence, proposed work must answer at least one of these questions:

```text
Does it clarify a contract?
Does it make compatibility testable?
Does it version/migrate persisted state?
Does it stabilize an extension point?
Does it close a production-readiness gap?
Does it provide real-world evidence for an existing capability?
```

If the primary answer is simply "it adds another capability/provider/platform responsibility", the
proposal is outside the V1 stabilization scope unless the product-scope document is explicitly
reopened and justified.

## 12. A1 freeze result

The product boundary is frozen for the remainder of the V1.0 stabilization roadmap as:

```text
V1.0 = reliable batch-ingestion framework contract
V1.0 != general-purpose orchestration/data/cloud platform
```

Later V1 milestones may consolidate the contracts inside this boundary, but they should not widen
the boundary without an explicit architecture decision.
