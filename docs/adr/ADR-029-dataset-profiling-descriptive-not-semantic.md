# ADR-029 — Dataset profiling is descriptive, not semantic inference

## Status

Accepted — V0.3.0-a2.

## Context

Quality triage benefits from row counts, null counts, distinct counts, duplicate counts, observed runtime types and simple ranges. Those statistics must not silently become a schema inference or business-anomaly engine.

## Decision

`DatasetProfiler` produces immutable `DatasetProfile` / `FieldProfile` values from the existing dependency-neutral `Dataset`.

Profiling is descriptive only. It reports observed Python runtime types and safe structural statistics. It does not infer emails, phone numbers, identifiers, dates from strings, domains, business rules, or probabilistic anomalies.

The implementation remains exact and materialized in V0.3. A future streaming profiler may introduce bounded/approximate statistics only behind an explicit contract.

## Consequences

- profiling is deterministic and easy to test;
- no Pandas/Polars/Arrow engine becomes mandatory;
- consumers retain control over semantic interpretation;
- profile output remains suitable for portable run evidence rather than becoming a hidden catalog schema.
