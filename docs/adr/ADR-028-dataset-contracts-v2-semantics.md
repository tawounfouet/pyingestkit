# ADR-028 — Dataset Contracts V2 extend validation without coercion

## Status

Accepted — V0.3.0-a1.

## Context

V0.2 established a dependency-neutral `Dataset` plus basic structural contracts. V0.3 needs a richer quality surface without turning contracts into normalizers or a large validation DSL.

## Decision

`FieldContract` adds:

- `allowed_values`;
- `pattern` using full-string regular-expression matching;
- `min_value` / `max_value`;
- `min_length` / `max_length`.

`DatasetContract` adds:

- `unique_together` composite uniqueness constraints;
- a logical `primary_key` constraint;
- `max_issues` as a deterministic bound on returned issue detail.

Validation never rewrites the input Dataset. Failed comparisons caused by incompatible runtime values become validation issues rather than implicit casts.

`ValidationIssue` may carry a compact safe preview, constraint identity and context. Full row values are not copied into issues.

## Consequences

- V0.2 contracts remain valid constructors and keep their semantics;
- validation becomes expressive enough for common ingestion-quality checks;
- business normalization still belongs to job packs;
- the core remains free of Great Expectations-style expression DSLs;
- issue volume can be bounded predictably for large invalid inputs.
