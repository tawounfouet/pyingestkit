# PyIngestKit V0.5.0-a2 — PostgreSQL Schema Mapping + COPY Bulk Load

A2 keeps the V0.5 `Target` contract introduced in A1 and upgrades the PostgreSQL implementation from a correctness-first INSERT foundation to the production bulk path.

```text
Dataset
  ↓
PostgresSchemaMapper
  ↓
existing-table compatibility check
  ↓
BEGIN
  ↓
psycopg COPY ... FROM STDIN
  ↓
COMMIT
  ↓
TargetLoadResult(rows_loaded=N)
```

## Mapping policy

```text
str            → TEXT
int            → BIGINT
float          → DOUBLE PRECISION
Decimal        → NUMERIC
bool           → BOOLEAN
date           → DATE
naive datetime → TIMESTAMP WITHOUT TIME ZONE
aware datetime → TIMESTAMPTZ
bytes          → BYTEA
None/missing   → SQL NULL
```

All-null columns have no inferred type and are accepted only because A2 requires an existing destination table. Mixed naive/aware datetimes, nested dict/list values and incompatible heterogeneous columns fail explicitly.

## COPY properties

- psycopg 3 driver-native row adaptation;
- explicit column ordering from `Dataset.fields`;
- psycopg identifier composition for schema/table/columns;
- no string-built SQL identifiers;
- transaction owned by SQLAlchemy Core;
- rollback on COPY serialization or destination constraint failures;
- `Decimal` is never converted to float;
- Unicode, tabs, newlines, quotes, NULL, dates/datetimes and BYTEA are integration-tested against real PostgreSQL.

## Still intentionally out of A2

- automatic table/schema creation;
- unbounded schema evolution;
- JSONB implicit mapping;
- staging/swap;
- `TRUNCATE_LOAD`;
- `REPLACE`;
- upsert;
- target-load idempotency;
- target-load metadata records.

Those belong to later V0.5 milestones.

## Manual performance baseline

With a PostgreSQL DSN in `PYINGEST_TEST_POSTGRES_DSN`:

```bash
python scripts/benchmark_postgres_copy.py --rows 100000
```

The benchmark is informational and guards architecture decisions; V0.5.0-a2 does not freeze a throughput SLA.
