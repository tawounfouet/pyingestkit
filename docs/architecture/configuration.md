# Configuration — V0.6.0 stable contract

PyIngestKit uses Pydantic for validated configuration and PyYAML for project files. Configuration models are frozen and reject unknown keys (`extra="forbid"`) so drift fails early.

## Runtime precedence

```text
framework defaults
        ↓
YAML project configuration
        ↓
--params-json
        ↓
--param / -p KEY=VALUE
        ↓
explicit CLI runtime options
```

`--param/-p` is repeatable and uses YAML scalar parsing.

## Stable object-storage schema

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

The V0.6.0 `S3ArtifactConfig` contract is limited to:

```text
bucket
prefix
region_name
endpoint_url_env
cache_path
```

Inline access keys, secret keys, session tokens, passwords, and provider-specific secret fields are not accepted by the project configuration model. Credentials are resolved by boto3 through its standard provider chain.

For AWS S3, `endpoint_url_env` may be omitted/unset. For MinIO and other compatible services, set the named environment variable to the endpoint URL.

## Metadata and PostgreSQL targets

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL

targets:
  warehouse:
    type: postgres
    target_id: postgres.demo.versioned
    dsn_env: PYINGEST_TARGET_DATABASE_URL
    schema: public
    table: demo_dataset
    load_mode: replace
```

The environment contains the actual DSNs. The YAML contains only variable names and logical destination identity.

## Logging

```yaml
logging:
  level: INFO
  format: rich
  console: true
  file:
    enabled: false
    path: .pyingest/logs/pyingest.log
    level: DEBUG
    format: json
    max_bytes: 10000000
    backup_count: 5
```

Accepted console/file formats are `rich`, `plain`, and `json`. Secret-looking values are redacted at logging boundaries.
