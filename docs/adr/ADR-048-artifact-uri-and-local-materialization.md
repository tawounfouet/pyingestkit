# ADR-048 — Artifact identity uses a credential-free URI plus a local materialization

## Status
Accepted for V0.6.0-a1.

## Context

Before V0.6, `RawArtifact.path` served two different purposes:

1. durable identity of the persisted RAW object;
2. local filesystem path consumed by parsers.

That works on one host but cannot represent S3/MinIO without either teaching every parser about object storage or replacing a filesystem path with `s3://...` and breaking the V0.5 parser contract.

## Decision

PyIngestKit separates the two concepts:

```text
source_uri
  = where the bytes came from

storage_uri / ArtifactURI
  = canonical persisted object location

path
  = local materialization used by current parsers
```

`ArtifactURI` is a small framework-owned value object. It requires a URI scheme and rejects embedded credentials, query strings and fragments. It supports local `file://` locations and provides deterministic construction for `s3://bucket/key` without introducing an S3 dependency into the core.

`RawArtifact.path` remains available in V0.6.0-a1 for compatibility. New code should treat `RawArtifact.location_uri` as durable identity and `RawArtifact.local_path` as the parser-facing materialization.

## Consequences

- V0.5 parsers remain dependency-neutral and keep reading local files.
- remote stores can make object storage canonical while maintaining a bounded local cache/materialization.
- replay can resolve historical RAW by `storage_uri` through `ArtifactStore.read_bytes()`.
- object-storage credentials never become part of artifact identity.
- this does not turn `ArtifactStore` into a universal filesystem API.
