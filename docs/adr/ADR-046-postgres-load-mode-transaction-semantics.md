# ADR-046 — PostgreSQL content load modes share one atomic transaction boundary

## Status

Accepted — V0.5.0-b2.

## Context

V0.5.0-a2 introduced atomic APPEND through psycopg COPY. B2 must add destructive content refresh semantics without exposing half-cleared destinations or turning PyIngestKit into a schema-migration/staging framework.

## Decision

`PostgresTarget` supports three explicit content modes:

- `APPEND`: preserve existing rows, then COPY;
- `TRUNCATE_LOAD`: validate first, then `TRUNCATE TABLE`, then COPY;
- `REPLACE`: validate first, then `DELETE FROM`, then COPY.

Each load owns one SQLAlchemy transaction. For destructive modes, clearing and loading are committed together or rolled back together.

`REPLACE` preserves the table object/schema and deliberately uses DELETE semantics. B2 does not implement generic staging-table swap.

## Consequences

- failed destructive loads restore prior contents;
- Dataset/table incompatibility never clears the destination;
- `TRUNCATE_LOAD` and `REPLACE` remain semantically distinct on PostgreSQL;
- schema evolution, upsert and staging remain separate future concerns;
- A2 COPY remains the primary production bulk-write path.
