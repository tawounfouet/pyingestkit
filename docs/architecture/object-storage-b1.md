# PyIngestKit V0.6.0-b1 — Remote Artifact Lifecycle + Reports / Manifest Object Storage

B1 expands the A2 S3 boundary from immutable RAW to the complete **run-artifact JSON lifecycle**.

```text
                       durable object storage
                              │
Source ──► RAW ───────────────►│ s3://.../raw/...             create-once
                              │
Dataset / validation / diff   │
        │                     │
        ├──► reports ─────────►│ s3://.../reports/*.json      run-scoped updates allowed
        │                     │
        └──► manifest ────────►│ s3://.../manifest.json       provisional → final
                              │
                              ▼
                    local materialization cache
                    .pyingest/runs/.../...
```

## Contract

`StoredArtifact` is the non-RAW durable reference:

```text
StoredArtifact
├── relative_path
├── path              local materialization
├── storage_uri       durable file:// or s3:// identity
├── content_type
├── size_bytes
└── sha256
```

`ArtifactStore` gains only additive concrete helpers:

```text
write_json_artifact(...) -> StoredArtifact
materialize_artifact(...) -> Path
```

No new abstract method is imposed on third-party V0.5 stores.

## S3 behavior

`S3ArtifactStore.write_json(...)` now uploads JSON run artifacts to the same deterministic run-relative key used by `uri_for(...)`, stores SHA-256 metadata, and keeps the local path as a cache/materialization.

The lifecycle deliberately differs by artifact class:

```text
RAW                       reports / manifest
-----------------------   ------------------------------
immutable create-once     run-scoped deterministic key
If-None-Match: *          rewrite allowed within run
provenance boundary       operational run artifacts
SHA-256 verified          SHA-256 verified
```

This distinction is required because `manifest.json` is finalized more than once and `reports/validation.json` can accumulate validations during one run.

## Operational recovery

B1 proves that after deleting local cache copies:

1. report bytes can be rematerialized from S3;
2. SHA-256 is verified;
3. the run manifest can be rematerialized;
4. `pyingest status --config ...` can read the remote manifest directly;
5. strict RAW replay still succeeds;
6. the replay manifest, including replay lineage, is persisted remotely.

## Still out of scope

B1 does **not** remote DatasetVersion snapshots, PublishedDataset pointers, or publication candidate/published datasets. Those belong to the next V0.6 milestone.
