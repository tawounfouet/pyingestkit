# PyIngestKit V2 — LOT-08 Version Store & Publication Foundation

LOT-08 turns the logical `DatasetVersion` introduced by LOT-07 into durable,
immutable version history plus an atomic current publication pointer.

## Boundary

```text
LOT-07 DatasetVersion
        |
        v
DatasetVersionStore
        |
        +--> immutable snapshot
        +--> DatasetVersionReference(locator=...)
        |
        v
DatasetPublisher
        |
        v
PublishedDataset
        |
        v
atomic current pointer
```

The persistence port and publication port are deliberately separate. A version
may exist durably without being published.

## Local reference profile

The first LOT-08 adapter is filesystem-only:

```text
versions/<dataset-id>/<version-id>/
  snapshot.json
  version.json

published/<dataset-id>/
  current.json
```

Version directories are immutable. Re-putting an already stored
content-addressed version is idempotent only when the durable snapshot verifies
against the requested version id.

`current.json` is the only mutable object in the local publication lifecycle.
It is replaced atomically, so readers observe either the previous complete
pointer or the new complete pointer.

## Snapshot contract

Snapshot bytes contain only portable schema evidence and the exact decoded
representation. Provider SDK objects, dataframe types, run-local paths,
credentials and publication state are forbidden.

Reading a snapshot recomputes both schema and content fingerprints and fails
closed on tampering.

## Compatibility

The stable V1 `pyingestkit.versioning` and `pyingestkit.publication` export
sets remain unchanged. V2 contracts live under qualified V2 modules and the
V2-only `pyingestkit.stores` namespace during the transition.

## Deferred

This foundation does not yet add:

- S3/object-storage DatasetVersion adapters;
- SQL metadata persistence;
- distributed publication locks;
- retention/garbage collection;
- rollback UX;
- replay.

Those capabilities remain later roadmap work.
