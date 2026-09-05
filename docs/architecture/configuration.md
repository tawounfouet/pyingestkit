# Configuration — V1 stable candidate contract

PyIngestKit uses Pydantic for validated configuration and PyYAML for project files. Configuration
models are frozen and reject unknown keys (`extra="forbid"`) so drift fails early.

## Configuration-file precedence

```text
explicit --config
  -> PYINGEST_CONFIG
  -> PYINGEST_ENV -> pyingest.yml.<env>
  -> pyingest.yml / pyingestkit.yml / .pyingest.yml
  -> in-memory defaults
```

Explicit environment/profile selectors are fail closed. If the selected path/profile is missing,
configuration fails instead of silently falling through.

## Workspace precedence

```text
explicit --workspace
  -> PYINGEST_WORKSPACE
  -> runtime.workspace
  -> .pyingest
```

## Dotenv policy

Only current-working-directory dotenv files are considered. Profile files are
`envs/.env.<env>` then `.env.<env>`, followed by root `.env`. OS environment values always win.
Files ending in `.example` are templates and are never auto-loaded.

## Runtime parameters

```text
framework/YAML runtime.parameters
        ↓
--params-json
        ↓
--param / -p KEY=VALUE
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

`S3ArtifactConfig` contains no inline credentials. Boto3 resolves credentials through its standard
provider chain.

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

The environment contains the actual DSNs. YAML contains only variable names and logical destination
identity.

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

Console formats are `rich`, `plain` and `json`. File formats are `plain` and `json`; `rich` is a
terminal renderer and is rejected for file logging.

See [V1 operational stability contract](../reference/stability-v1.md).
