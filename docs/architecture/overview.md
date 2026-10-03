# Architecture overview

PyIngestKit 2.0 is a focused ingestion framework. It owns **how to ingest**; an external orchestrator owns **when to run**.

```text
External orchestrator
        │
        │ invokes
        ▼
IngestionDefinition
        │
        ▼
 IngestionRuntime.run(...)
        │
        ├── SourceConnector
        │      │
        │      ▼
        │   acquisition
        │      │
        │      ▼
        │   immutable RAW
        │   ArtifactReference
        │
        ├── Decoder
        │      │
        │      ▼
        │   validation /
        │   quality evidence
        │
        ├── DatasetVersionStore
        │      │
        │      ▼
        │   immutable
        │   DatasetVersion
        │
        └── explicit downstream actions
               ├── DatasetPublisher
               ├── DatasetTargetV2
               └── strict replay / verification
```

## Core boundaries

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

Provider implementations are replaceable. Durable public contracts use portable references rather than boto3 clients, SQLAlchemy engines, open file handles or DataFrames.

## Lifecycle invariants

PyIngestKit 2.0 keeps several distinctions explicit:

```text
ArtifactStore       != DatasetVersionStore
ArtifactStore       != publication target
DatasetVersion      != provider object version
Replay              != new source acquisition
PyIngestKit         != orchestrator
```

The framework preserves durable RAW evidence, creates immutable DatasetVersion identity, separates write from publication, and keeps target materialization explicit.

## Replay

Strict replay starts from preserved historical evidence, allocates a new `IngestionRunId`, and verifies the resulting immutable dataset identity. Missing or inconsistent replay evidence fails closed; the runtime does not silently reacquire the source.

## Transformation boundary

Business-domain transformation remains outside the ingestion core. PyTransformKit integration uses portable references rather than sharing provider clients or in-memory DataFrames as durable framework contracts.

```text
PyIngestKit DatasetVersionReference
        ↓
portable ResourceReference
        ↓
PyTransformKit InputBinding
        ↓
transformation output resource
        ↓
PyIngestKit governed DatasetVersion
        ↓
explicit publication
```

## Product boundary

PyIngestKit does not absorb distributed scheduling, worker fleets, generic DAG orchestration, IAM, catalog, GUI/SaaS, cloud provisioning or infrastructure administration into its core runtime.

## Detailed architecture records

- [V2 baseline](v2-lot00-baseline.md)
- [Ingestion runtime](v2-lot10-ingestion-runtime.md)
- [Strict replay](v2-lot11-strict-replay.md)
- [HTTP acquisition](v2-lot13-http-acquisition.md)
- [PostgreSQL target](v2-lot14-postgres-target.md)
- [S3 object storage](v2-lot15-s3-object-storage.md)
- [Canonical serialization](v2-lot16-canonical-serialization.md)
- [PyTransformKit integration](v2-lot17-pytransformkit-integration.md)
- [V1 semantic migration](v2-lot18-v1-semantic-migration.md)
- [Provider / port conformance](v2-lot19-provider-port-conformance.md)
- [Customer 360 beta gate](v2-lot20-customer360-beta-gate.md)
