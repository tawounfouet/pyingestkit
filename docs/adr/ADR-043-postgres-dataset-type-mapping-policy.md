# ADR-043 — PostgreSQL Dataset type mapping is deterministic and conservative

**Status:** Accepted for V0.5.0-a2  
**Date:** 2026-09-04

## Context

`Dataset` is intentionally dependency-neutral and stores Python values rather than a dataframe/Arrow schema. PostgreSQL bulk loading nevertheless needs explicit, reproducible type expectations and must detect incompatible destination schemas before sending rows.

## Decision

V0.5.0-a2 introduces a PostgreSQL-specific schema mapper outside the framework `Dataset` contract. It infers types from non-null values using the following policy:

| Python value | PostgreSQL expectation |
|---|---|
| `str` | `TEXT` |
| `int` | `BIGINT` |
| `float` | `DOUBLE PRECISION` |
| `Decimal` | `NUMERIC` |
| `bool` | `BOOLEAN` |
| `date` | `DATE` |
| naive `datetime` | `TIMESTAMP WITHOUT TIME ZONE` |
| aware `datetime` | `TIMESTAMPTZ` |
| `bytes` / byte-like | `BYTEA` |
| only missing / `None` | `UNKNOWN`, resolved only against an existing table |

`int + float` promotes deterministically to `DOUBLE PRECISION`. Other heterogeneous logical types fail explicitly. Naive and timezone-aware datetimes must never be mixed silently. Nested mapping/list values are rejected in A2; JSONB requires a future explicit mapping rather than implicit serialization.

A2 validates against an **existing** table. This is schema mapping, not schema migration. Automatic production schema evolution remains out of scope.

## Consequences

- Dataset remains engine-neutral;
- Decimal precision is not discarded through float conversion;
- timezone behavior is explicit and testable;
- schema drift becomes a controlled `TargetConfigurationError` before COPY;
- future explicit JSON/DDL policies can be added without changing Dataset.
