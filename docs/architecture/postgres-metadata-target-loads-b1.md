# PyIngestKit V0.5.0-b1 — PostgreSQL Metadata Hardening + Target Load Records

B1 makes target materialization queryable without collapsing the architectural boundary between `Target` and `MetadataStore`.

```text
TargetLoadRequest
  ↓
Target / PostgresTarget
  ↓
TargetLoadResult
  ↓
TargetLoadRecord
  ↓
TargetLoadMetadataCapability
  ↓
Memory / SQLite / PostgreSQL MetadataStore
```

## Target-load record

One `load_id` identifies one materialization attempt. The persisted record contains:

- `run_id`;
- `target_id`;
- `dataset_id`;
- optional `dataset_version_id`;
- load `mode` and terminal/lifecycle `status`;
- credential-free destination identity;
- input / loaded / verified row counts;
- start / completion / duration;
- bounded numeric metrics;
- optional error, redacted before built-in persistence;
- creation timestamp.

The `target_loads` table is additive and references `runs.run_id` with `ON DELETE CASCADE`. It is indexed for operational queries by run, dataset, target+destination, and status.

## Update semantics

`record_target_load()` is insert-or-update by `load_id`.

This deliberately supports a future lifecycle such as:

```text
RUNNING
  ↓
SUCCESS | FAILED | ROLLED_BACK
```

without implementing B2 idempotency. B1 does not decide whether a future load should run, skip, replace, truncate, or reuse a prior result.

## Compatibility

`TargetLoadMetadataCapability` remains separate from the abstract `MetadataStore` contract. Third-party metadata stores implemented against V0.4 remain valid without adding new abstract methods.

Built-in Memory, SQLite and PostgreSQL stores implement the capability.

## PostgreSQL metadata hardening

`PostgresMetadataStore` now follows the same credential-safe diagnostic boundary as `PostgresTarget`:

- raw DSNs are internal only;
- `safe_dsn` renders passwords hidden;
- initialization errors redact credential-bearing connection strings;
- SQLAlchemy Core remains the persistence engine;
- psycopg remains optional through the `postgres` extra.

## Still intentionally out of B1

- `TRUNCATE_LOAD`;
- `REPLACE`;
- staging/swap;
- upsert;
- target-load idempotency decisions;
- automatic orchestration of target execution.

Those remain V0.5.0-b2 / RC concerns.
