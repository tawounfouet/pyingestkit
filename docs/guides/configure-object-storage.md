# Configure S3-compatible object storage

Install the optional S3 adapter:

```bash
pip install "pyingestkit[s3]"
```

Configure the artifact backend without embedding credentials:

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

Credentials come from the standard boto3/AWS provider chain. PyIngestKit does not accept access keys in its YAML model.

For AWS S3, `endpoint_url_env` may be omitted or left unset. For MinIO or another S3-compatible service, set the referenced environment variable.

V0.6.0-b2 stores RAW, reports, run manifests, DatasetVersion snapshots/version metadata and PublishedDataset pointers in S3-compatible object storage. The local workspace remains a cache and parser-facing materialization area; Dataset version discovery and publication no longer require a shared local filesystem.
