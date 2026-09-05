# ADR-044 — psycopg 3 COPY is the PostgreSQL production bulk-load path

**Status:** Accepted for V0.5.0-a2  
**Date:** 2026-09-04

## Context

V0.5.0-a1 intentionally used a conservative parameterized INSERT foundation to validate the Target transaction boundary. A production ingestion framework must not make per-row INSERT the primary path for meaningful PostgreSQL datasets.

## Decision

For a real PostgreSQL dialect, `PostgresTarget` uses psycopg 3 `COPY ... FROM STDIN` with `Copy.write_row()` inside the SQLAlchemy-owned transaction.

The COPY statement is composed from psycopg `Identifier` objects; schema/table/column order is explicit and stable. Dataset values are passed as Python values to psycopg adaptation rather than manually constructing text COPY payloads. Missing fields and `None` become SQL NULL. `Decimal`, dates, datetimes and byte values retain their Python types.

The transaction remains:

```text
BEGIN
  ↓
reflect + validate existing table
  ↓
COPY ... FROM STDIN
  ↓
COMMIT
```

Any COPY/constraint failure escapes the COPY context and causes the enclosing transaction to roll back. The SQLAlchemy INSERT path remains only as a non-PostgreSQL test-harness fallback; it is not the production PostgreSQL strategy.

## Consequences

- PostgreSQL A2 advertises `bulk_load = true`;
- COPY performance can evolve internally without changing `Target.load()`;
- serialization and DB constraint errors preserve all-or-nothing semantics;
- staging, replace semantics and idempotency are still deferred to B2.
