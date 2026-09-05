# ADR-054 — S3 DatasetVersion storage is immutable; publication is one mutable pointer

Status: Accepted for V0.6.0-b2.

## Context

V0.6.0-b1 made RAW, reports and run manifests durable in S3-compatible object storage, but
`DatasetVersion` snapshots and `PublishedDataset` pointers still depended on a local filesystem.
That prevented a second runner with an empty workspace from discovering and loading the version
published by a first runner.

## Decision

PyIngestKit provides `S3DatasetVersionStore`, implementing the existing `DatasetVersionStore`
contract by composing the configured `S3ArtifactStore`.

The object namespace is deterministic:

```text
<prefix>/datasets/versions/<dataset path>/<version_id>/dataset.snapshot.json
<prefix>/datasets/versions/<dataset path>/<version_id>/version.json
<prefix>/datasets/published/<dataset path>/current.json
```

Dataset snapshots and version metadata are immutable create-once objects. Their identity remains
the V0.4 content-addressed Dataset fingerprint, and the V0.4 typed snapshot codec remains version
`1` unchanged.

`current.json` is the only mutable object in this version-store lifecycle. Publishing replaces that
single key. S3 PutObject replacement is atomic at the object-key boundary, so readers observe an
old or new complete pointer, never a partially written local file.

All B2 objects carry `pyingestkit-sha256` metadata. Reads verify the object bytes against that
metadata before decoding JSON or Dataset snapshots.

## Consequences

- Dataset versions and publication no longer require a shared local filesystem.
- A runner with an empty workspace can discover the current publication, list versions and load a
  snapshot directly from object storage.
- Existing `FilesystemDatasetVersionStore` semantics and the abstract `DatasetVersionStore`
  surface remain unchanged.
- `S3ArtifactStore` remains responsible for transport/configuration; B2 does not add methods to the
  abstract `ArtifactStore` contract.
- MetadataStore remains optional and independent from the durable version store.
- Multi-object distributed transactions, locking and compare-and-swap publication are not claimed
  by B2. Those concerns require a later coordination design if concurrent publishers demand them.
