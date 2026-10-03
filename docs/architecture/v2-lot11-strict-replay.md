# PyIngestKit V2 — LOT-11 Strict Replay Foundation

LOT-11 introduces strict replay from durable historical RAW while preserving the
V2 rule that replay is a **new semantic ingestion run**, not an internal retry.

## Core invariant

```text
historical source run
        |
        +--> durable RAW ArtifactReference
                 |
                 | open + SHA-256/size verification
                 v
            historical bytes
                 |
                 | materialize create-once copy
                 v
new IngestionRunId / replay RAW
                 |
                 v
IngestionRuntime.execute_from_raw()
                 |
                 +--> decode
                 +--> validate
                 +--> DatasetVersion candidate
                 +--> optional expected-version guard
                 |
                 v
            IngestionResult
```

The replay path does **not** resolve `SourceRegistry`, construct a source
connector or call the live source.

## Strict RAW semantics

A `ReplayRequest` requires:

- the historical `IngestionRunId`;
- an exact RAW `ArtifactReference`;
- SHA-256 integrity evidence;
- the current `IngestionDefinition`;
- an optional expected `DatasetVersionReference`.

Validation rules are supplied at the `ReplayServiceV2.replay(...)` execution
boundary rather than embedded in the immutable replay request.

Reading historical RAW goes through `ArtifactStore.open(...).read()`, so store
integrity checks remain authoritative. Replay then creates a new RAW artifact
under the new run. Its SHA-256 must equal the origin RAW SHA-256.

No live fallback exists in LOT-11.

## New run identity

A replay must allocate a new `IngestionRunId`. Reusing the source run id is a
contract violation.

Internal retries, by contrast, retain the existing run id. This distinction was
reserved in LOT-01 and becomes executable here.

## Version verification

When an expected dataset version is supplied, the downstream runtime computes
the candidate content-addressed version before persistence. A mismatch returns a
failed `IngestionResult` with `runtime.version_mismatch`; the mismatching
candidate is not persisted.

If no expected version is supplied, replay remains strict about RAW integrity
but does not claim exact output reproducibility.

## Publication safety

LOT-11 replay never republishes. The downstream runtime is always invoked with
`publish=False`.

A replay that reproduces an existing content-addressed version may therefore
reuse/deduplicate that immutable version while leaving the published pointer
unchanged.

## Compatibility

The stable V1 `pyingestkit.replay` exports are not changed. V2 values live at:

```python
from pyingestkit.replay.v2 import ReplayRequest, ReplayResult, ReplayServiceV2
```

## Deferred

LOT-11 does not yet add:

- automatic source-run metadata lookup;
- historical definition restoration;
- parameter override restoration/redaction;
- cross-host S3 replay qualification (LOT-15/LOT-18);
- SQL replay-lineage persistence;
- CLI replay UX;
- explicit replay publication.

Those concerns remain later roadmap work.
