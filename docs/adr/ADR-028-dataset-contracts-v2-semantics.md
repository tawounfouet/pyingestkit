# ADR-028 — Dataset Contracts V2 semantics

## Status

Accepted — PyIngestKit V0.3.0 Alpha 1.

## Context

V0.2 established `FieldContract` and `DatasetContract` for required/null/type/unique,
extra-field and row-count checks. V0.3 needs richer generic quality constraints while
preserving the strict boundary between validation and business normalization.

## Decision

`FieldContract` adds exact `allowed_values`, regex `pattern` using `re.fullmatch`,
`min_value` / `max_value`, and string-only `min_length` / `max_length` constraints.
No constraint casts or normalizes input values.

`DatasetContract` adds:

- `unique_together` for composite uniqueness;
- `primary_key` as a logical dataset key, not a database constraint;
- bounded issue collection through `max_issues` with explicit
  `ValidationResult.issues_truncated`.

The V0.2 issue codes are retained for pre-existing constraints. New V0.3 constraints
use stable additive codes such as `field.allowed_values`, `field.pattern`,
`dataset.unique_together`, `key.null`, and `key.duplicate`.

`ValidationIssue` gains optional `value_preview`, `constraint`, and compact `context`.
Value previews are bounded and secret-looking fields are redacted.

## Consequences

- V0.2 contract constructors remain valid.
- Validation remains deterministic and non-mutating.
- CSV strings are never coerced to satisfy numeric contracts.
- Composite keys can be checked before persistence without introducing SQL semantics.
- Validation reports can remain bounded on highly invalid datasets.
