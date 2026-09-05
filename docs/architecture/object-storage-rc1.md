# PyIngestKit V0.6.0-rc1 — Full Cross-Host Object Storage E2E

RC1 is a qualification milestone, not a new storage abstraction. It composes the already-qualified V0.1-V0.5 ingestion/versioning/target contracts with the V0.6 S3-compatible ArtifactStore and DatasetVersionStore implementations.

## Reference slice

The ninth installable reference job is:

```text
demo.versioned_s3
```

It deliberately combines remote RAW, quality reports, remote diff reports, remote DatasetVersion snapshots, remote PublishedDataset pointers, PostgreSQL target loading, PostgreSQL metadata, and strict replay.

## Cross-host qualification scenario

```text
HOST A / workspace A

revision V1
  -> RAW -> MinIO
  -> validate / profile
  -> fingerprint V1
  -> immutable snapshot V1 -> MinIO
  -> PostgreSQL REPLACE / EXECUTE
  -> publish current -> V1

revision V2
  -> RAW -> MinIO
  -> validate / profile
  -> diff V1/V2 -> reports/diff.json -> MinIO
  -> fingerprint V2
  -> immutable snapshot V2 -> MinIO
  -> PostgreSQL REPLACE / RELOAD
  -> publish current -> V2

workspace A is deleted

HOST B / empty workspace B
  -> same PostgreSQL metadata
  -> same MinIO bucket/prefix
  -> resolve source run V2
  -> read historical RAW by durable storage_uri
  -> live HTTP acquisition remains forbidden
  -> parse / validate / profile
  -> fingerprint == V2
  -> existing remote DatasetVersion V2 is reused
  -> PostgreSQL load decision == SKIP
  -> PublishedDataset remains V2
```

No local path from host A is required after the workspace is removed.

## RC1 invariants

The service-backed E2E asserts that V1/V2 RAW objects and DatasetVersion snapshots are durable; the V2 diff report remains readable after workspace A is destroyed; `PublishedDataset.current` resolves to V2 from workspace B; the source V2 run is resolved from PostgreSQL metadata; strict replay reconstructs `actual_fingerprint == expected_fingerprint == V2`; replayed RAW keeps the original SHA-256; replay materializes in workspace B; publication remains V2; and PostgreSQL idempotency returns `SKIP` with zero rows loaded.

## CI topology

RC1 adds a dedicated GitHub Actions tier containing both PostgreSQL 16 and MinIO. The existing Python 3.11/3.12/3.13, PostgreSQL regression, S3 regression, quality, security, build and clean-wheel smoke gates remain mandatory.

## Public API boundary

RC1 adds no new framework-level public API. The only new installable product surface is the reference job `demo.versioned_s3`.

## Official artifact

```text
pyingestkit-v0.6.0-rc1-object-storage-e2e.zip
```

Stable V0.6 promotion must not add a new major capability; it should freeze these contracts, finish release documentation/security guidance, run the final release-check and produce stable wheel/sdist artifacts plus checksums.
