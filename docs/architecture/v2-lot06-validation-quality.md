# V2 LOT-06 — Validation & Quality Foundation

## Status

Implementation slice for the PyIngestKit 2.0 target.

## Purpose

LOT-06 validates the dependency-neutral `DecodedRepresentation` delivered by LOT-05
without reintroducing the legacy `Runner`, dataframe engines, business normalization,
or profiling inference.

## Boundary

```text
RAW ArtifactReference
        |
        v
LOT-05 Decoder
        |
        v
DecodedRepresentation
        |
        v
LOT-06 ValidationRequest
        |
        +--> ValidationRuleV2*
        |
        v
ValidationResult
        |
        v
QualityEvidence
```

Validation is deterministic and non-mutating. Rules inspect decoded values exactly as
produced by the decoder. They do not cast strings, normalize business values, infer
semantic types, acquire sources, persist reports, or transform records.

## Foundation rules

LOT-06 provides the first V2 rules:

- `MinimumRowsV2`
- `RequiredFieldV2`
- `UniqueFieldV2`

Issue collection is bounded by `ValidationLimits.max_issues`. Truncation is explicit
through the maintained `ValidationResult.issues_truncated` contract.

## Quality evidence

`QualityEvidence` binds a validation result to:

- the native `IngestionRunId`;
- `CorrelationContext`;
- the source `ArtifactReference`;
- the decoder identity.

It is evidence, not a runtime service and not a persistence mechanism.

## Compatibility

The V1 validation and quality APIs remain available. LOT-06 extends the package
additively and keeps the V2-specific execution surface explicit.

## Deferred

The following are deliberately outside LOT-06:

- profiling and semantic inference;
- dataframe-engine validation;
- report persistence/materialization;
- legacy `Runner` observation;
- dataset contracts beyond the three foundation rules;
- business normalization or transformation;
- SQL quality storage.

## Acceptance criteria

- V1 public API remains compatible.
- Validation consumes `DecodedRepresentation` directly.
- Rules are deterministic and non-mutating.
- Issue collection is bounded and reports truncation.
- Validation/quality V2 boundaries do not import pandas, Polars, PyArrow, DuckDB,
  SQLAlchemy, PyTransformKit, or PyWorkflowKit.
- No V2 validation contract depends on the legacy `Runner`.
- Architecture, public-contract and unit tests qualify the slice.
