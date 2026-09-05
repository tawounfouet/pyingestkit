# PyIngestKit V0.5.0-b2 — Load Modes + Transaction Semantics + Idempotency

V0.5.0-b2 turns the B1 target-load audit history into an operational execution contract without merging `Target` and `MetadataStore` responsibilities.

```text
TargetLoadRequest
  ↓
TargetLoadExecutor
  ├─→ TargetLoadMetadataCapability → prior target_loads
  │                              ↓
  │                   EXECUTE / SKIP / RETRY / RELOAD
  ↓
PostgresTarget
  ↓
ONE PostgreSQL transaction
  ├─ APPEND
  ├─ TRUNCATE_LOAD
  └─ REPLACE
  ↓
TargetLoadResult
  ↓
TargetLoadRecord
```

## Load-mode semantics

### APPEND

`APPEND` validates the existing destination schema and writes the Dataset with the existing psycopg 3 `COPY ... FROM STDIN` path. Existing rows are preserved.

### TRUNCATE_LOAD

`TRUNCATE_LOAD` performs, in one database transaction:

```text
reflect table
  ↓
validate Dataset ↔ table schema
  ↓
TRUNCATE TABLE
  ↓
COPY Dataset
  ↓
COMMIT
```

PostgreSQL `TRUNCATE` is used only after schema compatibility succeeds. Any subsequent COPY/database failure rolls the transaction back, restoring the prior table contents.

### REPLACE

`REPLACE` means transactional **content replacement while preserving the table object and schema**:

```text
reflect table
  ↓
validate Dataset ↔ table schema
  ↓
DELETE FROM table
  ↓
COPY Dataset
  ↓
COMMIT
```

This is intentionally distinct from `TRUNCATE_LOAD`: PostgreSQL DELETE semantics remain visible to triggers/foreign-key rules and identity/sequence state is not reset by PyIngestKit.

B2 does **not** redefine `REPLACE` as a staging-table swap. Generic staging/swap remains outside this milestone.

## Transaction boundary

Every `PostgresTarget.load()` attempt owns exactly one SQLAlchemy transaction. The destructive mutation and bulk load are never split across commits.

The invariant is:

```text
before load = A

successful destructive load
  → destination = B

failed destructive load
  → destination = A
```

`expected_row_count`, identifier checks and Dataset/table schema validation happen before destructive mutation.

## Idempotency identity

B2 uses the following logical identity when `dataset_version_id` is available:

```text
(target_id, dataset_id, dataset_version_id, destination, mode)
```

The decision is deterministic over persisted `target_loads` history:

| History | Decision |
|---|---|
| no equivalent history | `EXECUTE` |
| same version + destination + mode already `SUCCESS`/`SKIPPED` | `SKIP` |
| same identity most recently `FAILED`/`ROLLED_BACK` | `RETRY` |
| destination previously succeeded for another version or mode | `RELOAD` |
| same identity still `PENDING`/`RUNNING` | controlled conflict error |

`AUTO` is the default policy. Without `dataset_version_id`, AUTO executes and explicitly does **not** claim equivalence. `REQUIRE_VERSION` rejects unversioned requests. `DISABLED` bypasses history-based suppression.

## Separation of concerns

`PostgresTarget` never queries `MetadataStore`.

`TargetLoadExecutor` is a small local execution service that:

1. resolves the credential-free destination;
2. reads B1 target-load history;
3. decides `EXECUTE / SKIP / RETRY / RELOAD`;
4. records `RUNNING` before a physical attempt;
5. delegates the actual mutation to `Target`;
6. records `SUCCESS`, `SKIPPED`, `FAILED` or `ROLLED_BACK`.

This is not workflow orchestration, scheduling, queueing or distributed task execution.

## Metadata query hardening

`TargetLoadMetadataCapability.list_target_loads()` now supports optional filters for:

- `dataset_version_id`;
- `destination`;
- `mode`;

in addition to the B1 run/dataset/target/status filters.

No destructive migration of the B1 `target_loads` table is required.

## Deliberately out of B2

- UPSERT / MERGE;
- generic staging-table swap;
- schema evolution/migrations;
- distributed lock service or cross-database XA transaction;
- scheduler/orchestrator semantics;
- automatic replay-to-target behavior.

Those remain RC/stable or later-release concerns if demonstrated by real use cases.
