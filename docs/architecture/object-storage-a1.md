# PyIngestKit V0.6.0-a1 — ArtifactStore Contract Hardening + URI Abstraction

V0.6 is the object-storage line. Alpha 1 deliberately introduces **no cloud SDK**. Its purpose is to remove the implicit equation `artifact identity == local Path` while preserving the V0.5 parser and replay contracts.

## Contract

```text
External source
      ↓
 source_uri
      ↓
   RAW bytes
      ↓
ArtifactStore.write_raw
      ↓
RawArtifact
├── storage_uri / ArtifactURI  ← durable identity
├── path / local_path          ← parser materialization
├── sha256
├── size
└── provenance
```

For `LocalArtifactStore` both locations refer to the same object:

```text
storage_uri = file:///.../.pyingest/runs/.../raw/file.ndjson
path        = /.../.pyingest/runs/.../raw/file.ndjson
```

A future remote implementation may instead expose:

```text
storage_uri = s3://bucket/prefix/runs/.../raw/file.ndjson
path        = .pyingest/cache/.../raw/file.ndjson
```

## New framework capabilities

- `ArtifactURI` — credential-free storage locator;
- `ArtifactStore.uri_for()` — canonical object address;
- `ArtifactStore.read_bytes()` — URI-based byte resolution;
- `ArtifactStore.materialize_raw()` — local cache/materialization with SHA-256 verification;
- safe relative artifact path validation preventing `..`, absolute paths and backslash escapes;
- optional URI-aware artifact metadata with no SQL schema rewrite in A1;
- replay records preserve `origin_storage_uri` when available.

## Compatibility

The V0.5 ArtifactStore abstract surface is unchanged. The new methods have local defaults, so an implementation written against V0.5 is not made abstract by upgrading to A1.

Parsers remain unaware of S3. They still consume `RawArtifact.path`; the storage backend is responsible for ensuring that path is a valid local materialization.

## Explicitly deferred

- boto3/AWS S3 client;
- remote RAW upload/download;
- durable `s3://` location persistence in SQLite/PostgreSQL metadata;
- S3-compatible endpoint and MinIO hardening;
- remote reports/manifests;
- remote DatasetVersion snapshots/publication pointers.

Those start in V0.6.0-a2 and later milestones.
