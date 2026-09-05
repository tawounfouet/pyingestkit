# ADR-041 — Target abstraction exposes one atomic load operation

**Status:** Accepted for V0.5.0-a1  
**Date:** 2026-09-04

## Context

PyIngestKit already separates `ArtifactStore`, `MetadataStore`, version publication, and replay. V0.5 adds destination materialization without turning those persistence concerns into one database abstraction.

A first design could expose `prepare()`, `commit()`, and `rollback()` on the public `Target` contract. That would accidentally encode PostgreSQL transaction semantics into every future target.

## Decision

The public contract is intentionally narrow:

```text
Target
├── target_id
├── capabilities
├── open()
├── load(TargetLoadRequest) -> TargetLoadResult
└── close()
```

`load()` is the atomic materialization boundary. Backend-specific prepare/verify/commit/rollback operations remain implementation details. A backend may expose capabilities, but callers must not infer behavior from a backend class name.

`Target` remains distinct from:

- `ArtifactStore` — run artifacts and RAW bytes;
- `MetadataStore` — operational framework state;
- `DatasetVersionStore` — immutable dataset history;
- publication — canonical version pointer semantics.

## Consequences

- PostgreSQL can use transactions without imposing them on non-SQL targets.
- A2/B2 can replace internal insert/COPY/staging mechanics without breaking the high-level contract.
- Target loads can be tested as all-or-nothing operations.
- V0.5 does not become an ORM or a generic database session framework.
