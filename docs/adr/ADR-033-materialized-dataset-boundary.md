# ADR-033 — V0.3 keeps Dataset materialized and preserves a future streaming boundary

## Status

Accepted — V0.3.0-rc1.

## Context

NDJSON, Excel and especially Parquet make Dataset size limits visible. Retrofitting streaming into the existing V0.3 `Dataset` API during release-candidate hardening would silently change iteration, repeatability, profiling, validation and ownership semantics.

## Decision

V0.3 explicitly keeps the existing materialized immutable-ish Dataset contract. Parsers may provide defensive controls such as projection and `max_rows`, but they return a fully materialized Dataset.

Future support for very large datasets should introduce a separate buffered/streaming contract with explicit capabilities rather than changing the meaning of `Dataset`.

## Consequences

- V0.3 semantics remain deterministic and backwards compatible;
- the framework does not overclaim scalability;
- future streaming design remains possible without leaking generator lifetimes into current contracts;
- consumers can choose job-pack-specific Arrow/Polars/Pandas streaming or database-native paths today when their workload exceeds the V0.3 materialization envelope.
