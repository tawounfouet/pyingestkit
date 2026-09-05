# ADR-053 — S3 JSON run artifacts are durable while RAW remains create-once immutable

## Status
Accepted for V0.6.0-b1.

## Context

PyIngestKit writes some JSON artifacts more than once during a run. The run manifest is first
written provisionally and finalized after lifecycle hooks. Validation reporting may also rewrite an
aggregate `reports/validation.json` as validations accumulate. Applying RAW create-once semantics
to those files would break the existing lifecycle.

## Decision

For the S3 backend:

- RAW keeps ADR-051 create-once semantics with conditional object creation;
- JSON run artifacts are persisted at deterministic per-run keys and may be rewritten inside that
  run lifecycle;
- current JSON run artifacts are manifests and validation/profile/diff reports;
- every JSON object stores `pyingestkit-sha256` and `pyingestkit-artifact-kind` metadata;
- `application/json` is stored as the content type;
- the local workspace is a materialization/cache and the `s3://` URI is the durable identity;
- materialization from S3 verifies PyIngestKit SHA-256;
- ETag is not treated as a content hash.

A remote write occurs before the local temporary file is promoted to its final cache path. If the
remote write fails, the temporary local file is removed and the run receives a storage failure.

The `pyingest status` command uses the configured `ArtifactStore`, so an S3-backed manifest can be
read remotely when its local cache copy no longer exists.

## Out of scope

DatasetVersion snapshots and PublishedDataset pointers keep their V0.4/V0.5 filesystem semantics in
B1. They are migrated only in a later V0.6 milestone.
