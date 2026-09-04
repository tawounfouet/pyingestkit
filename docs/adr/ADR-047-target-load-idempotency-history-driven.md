# ADR-047 — Target-load idempotency is history-driven and remains outside Target

## Status

Accepted — V0.5.0-b2.

## Context

B1 made target materialization attempts queryable through `TargetLoadMetadataCapability`. Idempotency now needs to prevent duplicate APPENDs and unnecessary destructive reloads without coupling PostgreSQL target code to metadata persistence.

## Decision

Introduce `TargetLoadExecutor` and explicit `IdempotencyPolicy`, `IdempotencyAction` and `TargetLoadDecision` contracts.

When a Dataset version is available, equivalence is defined by:

```text
(target_id, dataset_id, dataset_version_id, destination, mode)
```

History maps deterministically to `EXECUTE`, `SKIP`, `RETRY` or `RELOAD`. Equivalent active loads produce a controlled conflict rather than a duplicate mutation.

`PostgresTarget` remains unaware of metadata. The executor records the B1 lifecycle around the target call.

## Consequences

- duplicate successful APPEND requests can be skipped safely;
- failed/rolled-back attempts become explicit retries;
- new Dataset versions become explicit reloads;
- unversioned AUTO requests execute without claiming idempotence;
- third-party Targets remain independent from the built-in metadata adapters;
- distributed locking and cross-database atomicity are not implied by this contract.
