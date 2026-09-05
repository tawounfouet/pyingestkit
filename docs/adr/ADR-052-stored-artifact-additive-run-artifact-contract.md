# ADR-052 — StoredArtifact is an additive run-artifact identity contract

## Status
Accepted for V0.6.0-b1.

## Context

A1 separated durable storage identity from local materialization for RAW. A2 made RAW durable in
S3 while keeping reports and manifests local. Extending object storage to non-RAW run artifacts
must not break the V0.5 `ArtifactStore.write_json(...) -> Path` contract used by built-in and
third-party stores.

## Decision

PyIngestKit adds `StoredArtifact` for non-RAW run artifacts. It carries:

- run-relative path;
- local materialization path;
- credential-free durable `storage_uri`;
- content type;
- byte size;
- SHA-256 integrity identity.

`ArtifactStore.write_json_artifact(...) -> StoredArtifact` and
`ArtifactStore.materialize_artifact(...) -> Path` are additive concrete methods. Existing stores
that only implement the V0.5 abstract surface continue to work: the default implementation calls
`write_json`, derives the local/file URI, computes SHA-256, and verifies materialization.

`RawArtifact` remains the acquisition/provenance model. `StoredArtifact` does not replace RAW and
does not introduce source HTTP metadata into reports or manifests.

## Consequences

- local and remote run artifacts share one durable-URI/materialization vocabulary;
- parsers remain unchanged and RAW remains a distinct immutable provenance boundary;
- third-party `ArtifactStore` subclasses do not need a mandatory interface migration;
- later V0.6 stores can reuse `StoredArtifact` for additional run-artifact classes.
