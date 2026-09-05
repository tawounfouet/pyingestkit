# ADR-045 — Target-load metadata is an additive run-linked capability

## Status

Accepted — V0.5.0-b1.

## Context

V0.5 introduces external persistence targets. Their materialization attempts need queryable audit
metadata, but extending the abstract `MetadataStore` interface would invalidate existing third-party
stores that correctly implement the V0.4 contract. `Target` must also remain independent from
metadata persistence.

## Decision

Introduce `TargetLoadMetadataCapability` as an optional metadata capability and persist
`TargetLoadRecord` values in an additive `target_loads` table.

Each record is keyed by stable `load_id` and linked to `runs.run_id`. It carries logical target,
dataset/version, destination, mode/status, row counts, timing, metrics and error information.
`record_target_load()` uses insert-or-update semantics by `load_id` so lifecycle state can be
updated without introducing idempotency decisions.

## Consequences

- custom V0.4 `MetadataStore` implementations remain valid;
- Memory, SQLite and PostgreSQL built-ins share one target-load metadata contract;
- target execution remains separate from metadata persistence;
- B2 can build idempotency/load-mode decisions on auditable history without changing B1 facts;
- raw credentials and DSNs are never part of target identity or persisted destination metadata.
