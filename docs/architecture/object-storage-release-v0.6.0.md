# PyIngestKit V0.6.0 — Stable Object Storage Contract

V0.6.0 is the stable promotion of the qualified RC1 object-storage line. It adds no capability beyond the RC; it freezes and documents the contracts proven by A1 → A2 → B1 → B2 → RC1.

## Stable architecture

```text
Source
  ↓
RAW ───────────────────────────────┐
  │                                │
  ▼                                │
Dataset → Validate/Profile → Diff  │
  │                                │
  ▼                                │
DatasetVersion snapshot            │
  │                                │
  ▼                                │
PublishedDataset pointer           │
  │                                │
  ├──────────────► PostgresTarget  │
  │                                │
  ▼                                │
Cross-host replay ◄────────────────┘
```

Durability responsibilities remain separated:

```text
ArtifactStore       = RAW / reports / manifests
DatasetVersionStore = immutable dataset snapshots + published pointer
MetadataStore       = runs / lineage / artifact locations / loads
Target              = consumable destination data
```

## Public API freeze

The exact top-level export set is guarded by `scripts/check_public_api.py`. V0.6.0 exposes the RC1 public surface unchanged, including `ArtifactURI`, `StoredArtifact`, `S3ArtifactStore`, and `S3DatasetVersionStore`.

No new framework-level symbol is introduced by stable promotion.

## Configuration freeze

The V0.6 stable S3 project configuration is intentionally narrow:

```text
bucket
prefix
region_name
endpoint_url_env
cache_path
```

Unknown fields are rejected. Credentials are outside the serialized config contract and use the boto3 provider chain.

## Error-contract freeze

Storage and replay failures remain framework-owned:

```text
IngestionError
├── StorageError
├── VersionStoreError
└── ReplayError
    ├── ReplayIntegrityError
    └── ReplayMismatchError
```

Provider-specific exceptions are translated at adapter boundaries where required; callers should depend on PyIngestKit errors rather than botocore internals.

## Stable object-storage invariants

- RAW is immutable and SHA-256 verified.
- DatasetVersion snapshots and version metadata are immutable/content-addressed.
- `PublishedDataset.current` is the mutable logical pointer.
- `source_uri` is provenance; `storage_uri`/artifact URI is durable artifact location.
- S3/MinIO never uses ETag as the PyIngestKit content hash.
- Local filesystem support remains first-class.
- boto3 remains optional through `pyingestkit[s3]`.
- strict replay performs no new source acquisition.
- remote replay must work after the original workspace is removed.
- PostgreSQL target idempotency remains valid across hosts.

## Security and CI hardening

Stable CI pins the MinIO image by digest and uses random ephemeral credentials in every MinIO job. The release gate covers Python 3.11/3.12/3.13, PostgreSQL 16, MinIO/S3 regressions, the combined cross-host scenario, public API freeze, Ruff formatting/lint, Mypy, Bandit, `pip-audit`, build, and isolated wheel smoke.

## Release artifacts

```text
pyingestkit-0.6.0-py3-none-any.whl
pyingestkit-0.6.0.tar.gz
pyingestkit_demo_jobs-0.6.0-py3-none-any.whl
pyingestkit_demo_jobs-0.6.0.tar.gz
pyingestkit-v0.6.0.zip
SHA256SUMS
```
