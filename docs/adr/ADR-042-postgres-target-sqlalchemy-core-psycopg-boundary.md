# ADR-042 — PostgresTarget uses SQLAlchemy Core with psycopg and no ORM

**Status:** Accepted for V0.5.0-a1  
**Date:** 2026-09-04

## Context

PyIngestKit V0.4 already ships SQLAlchemy Core for built-in metadata persistence and exposes `psycopg` through the optional `postgres` extra. V0.5 needs PostgreSQL destination loading and later needs psycopg COPY primitives.

## Decision

`PostgresTarget` keeps the existing dependency line:

```text
SQLAlchemy Core
    ↓
engine / connection / transaction / SQL primitives

psycopg 3
    ↓
PostgreSQL DBAPI driver and future COPY implementation
```

No SQLAlchemy ORM session, mapped class, Django model, or business entity identity is introduced.

The A1 implementation deliberately provides only a conservative parameterized `APPEND` path. It advertises `bulk_load = false`, `truncate_load = false`, `replace = false`, and `staging = false`. A2/B2 will enable those capabilities only when their semantics and tests exist.

Credentials remain external to YAML through `dsn_env`. Logical `target_id` values never contain connection strings. SQL schema, table, and Dataset field identifiers are restricted to safe standard PostgreSQL identifiers in A1.

## Consequences

- the optional PostgreSQL dependency remains governed rather than mandatory;
- the target is operational in A1 while not claiming COPY performance prematurely;
- rollback semantics are provided by one SQLAlchemy transaction per load;
- later COPY optimization can reuse the psycopg driver without changing the public Target contract.
