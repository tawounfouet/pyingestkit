# PyIngestKit V0.5.0-rc1 — Full PostgreSQL Persistence E2E

V0.5.0-rc1 closes the PostgreSQL persistence implementation line by proving the complete V0.4 version/replay lifecycle against the V0.5 target and metadata contracts.

## Reference slice

The eighth installable reference job is:

```text
demo.versioned_postgres
```

Its deterministic flow is:

```text
revision 1 RAW
  ↓
Dataset + validation + profile
  ↓
DatasetVersion V1
  ↓
PostgresTarget / REPLACE / COPY
  ↓
TargetLoadRecord action=EXECUTE status=SUCCESS
  ↓
publish V1

revision 2 RAW
  ↓
Dataset + validation + profile
  ↓
diff V1/V2 = +1 / -1 / changed 1 / unchanged 1
  ↓
DatasetVersion V2
  ↓
PostgresTarget / REPLACE / COPY
  ↓
TargetLoadRecord action=RELOAD status=SUCCESS
  ↓
publish V2

strict replay of revision 2
  ↓
historical RAW only; live HTTP forbidden
  ↓
fingerprint == V2
  ↓
TargetLoadExecutor sees the same V2/destination/mode
  ↓
TargetLoadRecord action=SKIP status=SKIPPED
  ↓
0 rows written; published pointer remains the live V2 publication
```

## Metadata matrix

The same slice is qualified twice on PostgreSQL 16:

1. `SQLiteMetadataStore` + `PostgresTarget`;
2. `PostgresMetadataStore` + `PostgresTarget`.

This proves that target materialization remains independent from metadata backend selection.

## Runtime observation

The reference job selects its metadata adapter explicitly from a non-secret backend parameter and reads PostgreSQL DSNs only from named environment variables. Target load results remain auditable through the B1 `target_loads` capability. No DSN or credential is serialized.

## PostgreSQL semantics inherited from B2

- `APPEND` is transactional COPY;
- `TRUNCATE_LOAD` is transactional TRUNCATE + COPY;
- `REPLACE` is transactional DELETE + COPY;
- destructive mutations happen only after schema compatibility validation;
- any COPY/constraint failure rolls the transaction back;
- idempotency is decided outside `Target` from target-load history.

## RC1 release gates

The RC is accepted only when the same commit passes:

- Python 3.11 / 3.12 / 3.13;
- unit, contract and integration suites;
- PostgreSQL 16 real integration;
- A2 COPY regression;
- B1 target-load metadata regression;
- B2 load-mode/idempotency regression;
- `demo.versioned_postgres` SQLite-metadata slice;
- `demo.versioned_postgres` PostgreSQL-metadata slice;
- strict RAW replay with network forbidden;
- Ruff + Ruff format + Mypy strict;
- Bandit + pip-audit;
- wheel + sdist build;
- clean-wheel smoke with all eight entry points visible.

No new target backend, scheduler, ORM, schema migration engine or object-storage capability is introduced by RC1.
