# PyIngestKit V0.6.0-a2 — S3ArtifactStore + Remote RAW

A2 turns the URI contract from A1 into a real remote storage backend.

```text
Source / Fixture
      ↓
   RAW bytes
      ↓
S3ArtifactStore
  ├── s3://bucket/prefix/runs/.../raw/file   ← durable immutable RAW
  └── .pyingest/runs/.../raw/file            ← local parser cache
      ↓
Parser → Dataset → existing V0.5/V0.6 pipeline
```

## Runtime configuration

```yaml
artifacts:
  backend: s3
  s3:
    bucket: my-pyingest-raw
    prefix: pyingest
    region_name: eu-west-3
    endpoint_url_env: PYINGEST_S3_ENDPOINT_URL
```

AWS credentials are obtained from the boto3 provider chain (`AWS_ACCESS_KEY_ID`, workload identity, instance/task role, profile, etc.). They are not fields in PyIngestKit YAML.

## Replay

Built-in SQL metadata stores persist `storage_uri` additively in `artifact_locations`. During strict replay, `storage_uri` wins over the historical local path. If the source-run cache is gone, the runner downloads the historical S3 RAW, verifies its SHA-256, materializes it locally, and writes the replay run's own immutable RAW object.

## A2 qualification

A real MinIO service in CI proves:

- remote object creation;
- `s3://` metadata persistence;
- object SHA metadata;
- local cache deletion;
- remote recovery;
- strict replay with matching Dataset fingerprint;
- a distinct immutable RAW object for the replay run.

## Still out of scope

- remote reports/manifests;
- remote DatasetVersion snapshots;
- remote `PublishedDataset` pointers;
- advanced MinIO/AWS addressing and endpoint hardening;
- multipart/large-object transfer tuning.

Those belong to later V0.6 milestones.
