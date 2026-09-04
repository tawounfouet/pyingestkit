# ADR-026 — Separate parser, normalizer, and dataset contract boundaries

## Status

Accepted — V0.2.0 Beta 1.

## Context

In ingestion jobs, serialization decoding, business cleanup, and validation are often mixed into one function. That makes reusable framework primitives hard to test and causes domain rules to leak into generic infrastructure.

## Decision

PyIngestKit separates three concerns:

```text
Parser          : RAW serialization -> Dataset
Normalizer      : business transformation -> job-pack concern
DatasetContract : Dataset -> ValidationResult
```

Framework CSV/JSON parsers do structural decoding only. They do not trim, rename, enrich, map codes, or perform business type conversions. `DatasetContract` validates without mutating the dataset.

## Consequences

- parser behavior remains deterministic and reusable across domains;
- raw-to-structured fidelity is easier to audit;
- business normalization stays in job packs;
- contracts can be tested independently and return structured validation issues;
- later parser formats can share the same `Dataset` and `DatasetContract` surfaces.
