# Configure S3-compatible object storage

PyIngestKit V0.6.0 stores durable RAW, run reports/manifests, DatasetVersion snapshots/metadata, and PublishedDataset pointers in S3-compatible object storage while keeping local materialization as a parser-facing cache.

## Install

```bash
pip install "pyingestkit[s3]"
```

## Minimal configuration

```yaml
runtime:
  workspace: .pyingest

artifacts:
  backend: s3
  s3:
    bucket: my-pyingest-artifacts
    prefix: pyingest
    region_name: eu-west-3
    endpoint_url_env: PYINGEST_S3_ENDPOINT_URL
    cache_path: .pyingest
```

Credentials are not accepted in this YAML model. PyIngestKit uses the standard boto3/AWS credential provider chain.

For AWS S3, `endpoint_url_env` can be omitted or left unset. For MinIO or another S3-compatible endpoint:

```bash
export PYINGEST_S3_ENDPOINT_URL='https://minio.example.internal'
```

## Durable identity vs local materialization

```text
artifact URI / storage_uri  = durable identity
local path / cache_path     = temporary materialization
```

A cross-host replay therefore needs access to the same metadata backend, object-storage bucket/prefix, installed job package, and configuration — not the filesystem of the original runner.

## Production security

Use private buckets and least-privilege bucket/prefix permissions. Prefer IAM roles, workload identity, OIDC/web identity, or other short-lived credentials to long-lived static keys. Use HTTPS outside local CI/development. Provider-side encryption may be enabled according to infrastructure policy; PyIngestKit does not provision IAM, buckets, lifecycle rules, or KMS keys.

Retention must keep historical RAW and immutable DatasetVersion objects for as long as replay/lineage guarantees require them. A lifecycle policy that deletes those objects invalidates replay by design.

## MinIO compatibility

MinIO is the V0.6 CI/reference S3-compatible backend. The stable CI pins the tested image by digest and creates random ephemeral credentials per job. PyIngestKit does not expose a separate `MinioArtifactStore`; MinIO is configured through `S3ArtifactStore(endpoint_url=...)`.

## Failure semantics

No automatic local fallback occurs when S3 is unavailable. Missing or corrupt historical artifacts fail explicitly. Replay does not reacquire the original HTTP/file source to hide remote-storage failure.
