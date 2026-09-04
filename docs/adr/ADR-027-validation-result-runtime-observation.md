# ADR-027 — ValidationResult is observable runtime output

- Status: Accepted
- Date: 2026-09-04

## Context

Beta 1 introduced `ValidationResult`, but validation was still a library-level operation. The V0.2 release candidate needs a complete acquisition slice in which validation is visible in the run manifest, metadata history, and structural events.

## Decision

`Runner` recognizes `ValidationResult` returned directly or inside common nested step outputs.

For each result it:

- appends the result to `RunManifest.validations` with the producing step name;
- persists one validation summary plus individual issues through `MetadataStore.record_validation`;
- emits `VALIDATION_COMPLETED`;
- converts results containing `ERROR` issues into a controlled `ValidationError`, after observability data has been recorded.

Warnings and review-severity issues do not fail the run.

## Consequences

Validation becomes a first-class ingestion lifecycle signal without coupling `DatasetContract` to `Runner` or `MetadataStore`. Jobs remain free to implement other validation producers as long as they return the framework `ValidationResult` contract.

This does not make every step a validator and does not introduce business normalization into parsers.
