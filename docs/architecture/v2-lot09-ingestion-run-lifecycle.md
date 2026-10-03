# PyIngestKit V2 — LOT-09 Ingestion Run Lifecycle

LOT-09 introduces the portable execution-lifecycle values required by the V2
target API without reintroducing the legacy Job/Pipeline/Step/Runner model.

## Boundary

```text
IngestionDefinition
        |
        v
IngestionRun
        |
        +--> IngestionRunId
        +--> CorrelationContext
        +--> definition fingerprint
        +--> lifecycle timestamps
        +--> IngestionStatus
        |
        v
IngestionResult
        |
        +--> DatasetVersionReference
        +--> optional PublishedDataset
        +--> diagnostics
        +--> optional FailureEvidence
```

LOT-09 models execution evidence only. It does not execute connectors, decoders,
validation rules, stores or publishers.

## Lifecycle invariants

`IngestionRun` is an immutable lifecycle snapshot:

- `CREATED` has neither `started_at` nor `ended_at`;
- `RUNNING` requires `started_at` and forbids `ended_at`;
- terminal states require `ended_at`;
- timestamps cannot move backwards;
- correlation run identity, when present, must match the native
  `IngestionRunId`.

`IngestionResult` is terminal-only. Successful results cannot carry
`FailureEvidence`; non-successful results must carry it. Failure and diagnostic
identities must match the run.

A published dataset can only appear together with its matching
`DatasetVersionReference`.

## Compatibility

The stable V1 `pyingestkit.runtime` namespace continues to export only
`Runner`. V2 lifecycle values are exposed through the qualified
`pyingestkit.runtime.v2` module until the 2.0 API cut.

## Deferred

LOT-09 deliberately does not implement:

- `IngestionRuntime` orchestration;
- automatic source acquisition;
- decode/validate/version/publish sequencing;
- retries or reconciliation loops;
- replay (LOT-11);
- provider adapters.

Those behaviors require a separate runtime/application layer and must not leak
into the domain lifecycle values.
