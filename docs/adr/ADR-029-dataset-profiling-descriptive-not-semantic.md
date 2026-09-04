# ADR-029 — Dataset profiling is descriptive, not semantic inference

## Status

Accepted — PyIngestKit V0.3.0 Alpha 2.

## Context

After V0.3 Alpha 1 can express richer quality expectations, users need a stable way to
describe the data actually observed. Binding profiling to a dataframe engine or semantic
type inference would violate the neutral `Dataset` boundary established in V0.2.

## Decision

`DatasetProfiler` is a separate framework service. It produces immutable
`DatasetProfile` / `FieldProfile` values with row/field counts, present/null/non-null
counts, exact distinct counts, stable observed Python type names, string length ranges,
numeric min/max when safe, and full-row duplicate counts.

The profiler never parses semantic dates, converts strings to numbers, maps codes, or
mutates `Dataset`. Nested Python/JSON structures use deterministic structural identities
for distinct/duplicate counting. No sample values are collected in Alpha 2.

## Consequences

- profiling remains engine-neutral and safe by default;
- CSV's string-preservation contract remains intact;
- mixed Python types are reported rather than coerced;
- profiles are suitable input for later diff/versioning work without becoming a data
  catalog or inference engine.
