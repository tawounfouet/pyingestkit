# PyIngestKit V2 — LOT-14 PostgreSQL Target

LOT-14 introduces PostgreSQL destination materialization for the V2 ingestion
model without reusing the legacy V1 `Target`, `Dataset` or
`TargetLoadRequest` contracts.

## Boundary

```text
DatasetVersionReference
        +
DecodedRepresentation
        |
        v
TargetLoadRequestV2
        |
        v
DatasetTargetV2
        |
        v
PostgresTargetV2
        |
        +--> reflect existing table
        +--> validate decoded types
        +--> prepare load mode
        +--> psycopg COPY FROM STDIN
        |
        v
TargetLoadResultV2
```

The request verifies the decoded representation content fingerprint against the
immutable `DatasetVersionReference.version_id` before target I/O begins.

## Atomicity

One `load()` call owns one SQLAlchemy transaction.

```text
BEGIN
  |
  +--> reflect destination
  +--> validate schema
  +--> optional DELETE/TRUNCATE
  +--> COPY ... FROM STDIN
  |
  +--> COMMIT on complete success
  |
  +--> ROLLBACK on COPY / constraint / provider failure
```

Destructive mode preparation happens only after schema validation and remains
inside the same transaction as COPY.

## Load modes

LOT-14 qualifies three explicit modes:

- `append` — preserve existing rows and append the version rows;
- `truncate_load` — transactional `TRUNCATE TABLE` followed by COPY;
- `replace` — transactional `DELETE` followed by COPY.

No mode is inferred from destination state.

## Schema policy

The V2 decoder currently owns portable JSON-like scalar values. LOT-14 maps:

| Decoded value | PostgreSQL expectation |
|---|---|
| `str` | text-compatible |
| `int` | integer-compatible |
| `float` | float/numeric-compatible |
| `bool` | boolean |
| null / missing only | destination-owned / unknown |

Nested `DecodedObject` and `DecodedArray` values fail closed. JSONB requires
an explicit future mapping rather than implicit serialization.

LOT-14 validates an existing destination table. It does not create or migrate
production schemas.

## COPY boundary

Real PostgreSQL loads use psycopg 3 `COPY ... FROM STDIN` while SQLAlchemy
owns the connection and transaction. Identifiers are composed using psycopg
`Identifier` objects and restricted to PostgreSQL-safe unquoted names.

## Dependency governance

`psycopg` remains optional behind the existing `postgres` extra.

SQLAlchemy remains temporarily in the base dependency line because maintained
V1 metadata/target behavior still depends on it. LOT-14 isolates provider
usage architecturally inside the PostgreSQL adapter; removing SQLAlchemy from
the V2 base is a 2.0 packaging-cut concern.

## Compatibility

Maintained V1 remains unchanged:

```python
from pyingestkit.targets import PostgresTarget
```

V2 uses:

```python
from pyingestkit.targets.v2 import (
    PostgresTargetV2,
    TargetLoadModeV2,
    TargetLoadRequestV2,
)
```

No V2 adapter imports `pyingestkit.targets` legacy execution contracts.

## Deferred

LOT-14 does not introduce:

- target-load history/idempotency metadata;
- automatic table creation or schema migration;
- UPSERT/MERGE;
- staging tables;
- distributed locks;
- replay-specific target suppression;
- runtime target orchestration.

Those concerns require separate roadmap contracts.
