# PyIngestKit V0.5.0 — PostgreSQL Persistence Targets Release

V0.5.0 promotes the PostgreSQL persistence line to stable without adding runtime features beyond the qualified RC1.

## Stable product scope

PyIngestKit can now materialize a validated and versioned `Dataset` into PostgreSQL through an explicit framework-owned `Target` contract while retaining independent artifact, metadata, versioning and replay boundaries.

The stable V0.5 surface includes:

- `Target` and `TargetCapabilities`;
- `TargetLoadRequest` and `TargetLoadResult`;
- `LoadMode.APPEND`, `LoadMode.TRUNCATE_LOAD`, and `LoadMode.REPLACE`;
- `PostgresTarget` backed by SQLAlchemy Core + psycopg 3;
- deterministic Dataset-to-PostgreSQL type compatibility planning;
- PostgreSQL `COPY ... FROM STDIN` bulk loading;
- transaction rollback on COPY/constraint failure;
- additive target-load metadata for Memory, SQLite and PostgreSQL stores;
- history-driven idempotency through `TargetLoadExecutor`;
- `EXECUTE`, `SKIP`, `RETRY`, and `RELOAD` decisions outside the Target contract.

## Stable PostgreSQL semantics

```text
APPEND
  → validate schema
  → COPY
  → COMMIT

TRUNCATE_LOAD
  → validate schema
  → TRUNCATE
  → COPY
  → COMMIT

REPLACE
  → validate schema
  → DELETE
  → COPY
  → COMMIT
```

For destructive modes, schema compatibility is checked before the table is mutated. The mutation and COPY share one PostgreSQL transaction, so a failure rolls the target back to its previous state.

## Idempotency boundary

`PostgresTarget` does not query metadata. `TargetLoadExecutor` consults target-load history and applies the V0.5 identity:

```text
(target_id, dataset_id, dataset_version_id, destination, mode)
```

The default history-driven behavior is deterministic:

```text
no prior equivalent success → EXECUTE
same successful version     → SKIP
prior failed/rolled back    → RETRY
other version/mode loaded   → RELOAD
active equivalent load      → CONFLICT
```

## Qualified reference flow

The eighth reference job, `demo.versioned_postgres`, proves:

```text
V1 RAW → DatasetVersion V1 → PostgreSQL → publish V1
V2 RAW → diff V1/V2 → DatasetVersion V2 → RELOAD → publish V2
replay V2 from historical RAW → same fingerprint → idempotent SKIP
```

The flow is qualified with both:

- SQLite metadata + PostgreSQL target;
- PostgreSQL metadata + PostgreSQL target.

PostgreSQL 16 is used as the real CI service.

## Compatibility matrix

V0.5.0 is qualified on Python 3.11, 3.12 and 3.13. SQLite remains the default metadata backend. PostgreSQL metadata and PostgreSQL target support remain behind the `postgres` extra. Excel and Parquet remain optional extras.

## Explicitly out of scope

V0.5.0 does not add:

- S3 / MinIO object storage;
- Snowflake, BigQuery or SQL Server targets;
- a generic multi-database target abstraction;
- generic UPSERT semantics;
- an ORM;
- a schema migration framework;
- CDC or streaming;
- a scheduler, DAG orchestrator or distributed execution runtime.

Object storage remains a conditional V0.6 milestone driven by pilot evidence.

## Release invariant

The stable release is a promotion of RC1. Any functional correction after release must be delivered through an appropriate patch release such as `v0.5.1`; V0.5.0 itself is immutable once tagged.
