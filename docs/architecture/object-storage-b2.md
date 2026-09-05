# PyIngestKit V0.6.0-b2 — Remote DatasetVersion + Publication Object Storage

B2 closes the remaining filesystem dependency in the V0.4 Dataset versioning lifecycle.

```text
Runner A / workspace A
        │
        ├── Dataset ──► fingerprint ──► immutable snapshot ───────┐
        │                                                        │
        └── publish ───────────────► current.json                 │
                                                                 ▼
                                                   S3-compatible object storage
                                                                 │
Runner B / empty workspace B                                    │
        │                                                        │
        ├── get_published() ◄────────────────────────────────────┤
        ├── get_version()   ◄────────────────────────────────────┤
        ├── load_dataset()  ◄────────────────────────────────────┤
        └── create V2 + publish ─────────────────────────────────►│
```

## Durable namespace

For `dataset_id=demo.cross_host`:

```text
s3://<bucket>/<prefix>/datasets/versions/demo/cross_host/<version_id>/dataset.snapshot.json
s3://<bucket>/<prefix>/datasets/versions/demo/cross_host/<version_id>/version.json
s3://<bucket>/<prefix>/datasets/published/demo/cross_host/current.json
```

The dataset ID and version ID are validated before becoming object-key components.

## Semantics

`S3DatasetVersionStore` implements the existing `DatasetVersionStore` contract. It does not alter
`DatasetVersion`, `PublishedDataset`, Dataset fingerprinting, or `SnapshotCodec` version `1`.

| Object | Lifecycle | Integrity |
| --- | --- | --- |
| `dataset.snapshot.json` | immutable / create-once | SHA-256 metadata + fingerprint verification |
| `version.json` | immutable / create-once | SHA-256 metadata |
| `current.json` | mutable publication pointer | SHA-256 metadata + referenced-version verification |

A retry that finds a previously created snapshot verifies that the stored snapshot still resolves
to the same content-addressed version before completing missing version metadata.

## Runtime and CLI

`demo.versioned_ndjson` selects the S3-backed version store automatically when its run uses an
`S3ArtifactStore`; local runs continue to use `FilesystemDatasetVersionStore`.

`pyingest versions` and `pyingest published` now accept `--config`. With an S3 artifact backend
they inspect the remote version store and therefore do not require a pre-existing local workspace.

## B2 qualification target

The MinIO-backed E2E proves:

1. Runner A creates and publishes V1.
2. Workspace A disappears.
3. Runner B starts with an empty workspace, discovers V1 and loads its Dataset remotely.
4. Runner B creates/publishes V2 and lists V1 + V2.
5. CLI `versions` and `published` read the same remote state.
6. Runner C, again with an empty workspace, resolves and loads V2.

This is the first V0.6 milestone where Dataset version state is portable across runner-local
filesystems. Full cross-host run/replay qualification remains the purpose of V0.6.0-rc1.
