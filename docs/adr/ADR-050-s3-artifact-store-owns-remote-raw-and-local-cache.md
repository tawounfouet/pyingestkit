# ADR-050 — S3ArtifactStore owns remote RAW and a local parser cache

## Status
Accepted for V0.6.0-a2.

## Decision

`S3ArtifactStore` makes `s3://bucket/key` the canonical location of RAW bytes while preserving a local materialization under the configured workspace/cache root. Parsers remain object-storage-neutral and continue consuming `RawArtifact.path`.

A2 uploads **RAW only**. Manifests, reports and DatasetVersion snapshots remain local. The object key is deterministic from prefix, job id, run id and sanitized RAW name. Credentials are never accepted in YAML or artifact URIs; boto3 uses the standard AWS credential provider chain.

The store supports AWS S3 and S3-compatible endpoints through an optional endpoint URL supplied indirectly from an environment variable.
