# V1 Production-like Pilot — PostgreSQL + S3-compatible object storage

This guide turns the B2 cross-host qualification topology into an operator-oriented pilot. It uses
existing PyIngestKit capabilities only; infrastructure provisioning and scheduling stay outside the
framework.

## 1. Target topology

```text
Source / fixture
      |
      v
PyIngestKit Runner
      |
      +--> S3-compatible ArtifactStore
      |      RAW / reports / manifests
      |      DatasetVersion snapshots / publication pointer
      |
      +--> PostgreSQL MetadataStore
      |      runs / steps / artifacts / lineage / target loads
      |
      +--> PostgreSQL Target
             consumable dataset
```

Local workspace/cache is disposable. Durable recovery depends on the configured PostgreSQL and object
storage services.

## 2. Install the required extras

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,postgres,s3]"
python -m pip install -e examples/plugin_package
```

For a consumer project, install only the extras it actually needs.

## 3. Supply credentials outside YAML

Copy the staging environment template to a real dotenv file or inject the same variables with your
runtime secret manager:

```bash
cp envs/.env.stg.example envs/.env.stg
```

The example template is never auto-loaded. Populate real values before starting services or running a
job.

Typical service variables include PostgreSQL DSNs plus the standard AWS/boto3 credential chain and,
for a non-AWS S3-compatible endpoint, the endpoint variable named by the YAML configuration.

Never put database passwords, access keys or session tokens directly in project YAML.

## 4. Local service-backed staging pilot

The repository includes `docker-compose.staging.yml` for a local PostgreSQL + MinIO topology. Required
credentials are fail-closed environment variables; the compose file does not ship working passwords.

After supplying the required environment values:

```bash
docker compose -f docker-compose.staging.yml up -d
```

Verify the selected profile before ingestion:

```bash
PYINGEST_ENV=stg pyingest config
PYINGEST_ENV=stg pyingest jobs
PYINGEST_ENV=stg pyingest inspect demo.versioned_s3
```

If a selected profile is missing or invalid, fix the configuration rather than relying on fallback.

## 5. Run the cross-host reference slice

The repository-level deterministic config is:

```text
examples/plugin_package/demo-versioned-s3.yml
```

Run two revisions:

```bash
pyingest run demo.versioned_s3 \
  --config examples/plugin_package/demo-versioned-s3.yml \
  --param revision=1

pyingest run demo.versioned_s3 \
  --config examples/plugin_package/demo-versioned-s3.yml \
  --param revision=2
```

Inspect the resulting durable state:

```bash
pyingest versions demo.versioned_s3 \
  --config examples/plugin_package/demo-versioned-s3.yml

pyingest published demo.versioned_s3 \
  --config examples/plugin_package/demo-versioned-s3.yml

pyingest runs --config examples/plugin_package/demo-versioned-s3.yml
pyingest status --config examples/plugin_package/demo-versioned-s3.yml
```

## 6. Recovery test: treat local workspace as disposable

The defining B2 production-like proof is not merely writing to object storage. It is proving that a
fresh runner can recover historical durable state.

Before reproducing this test against any non-ephemeral environment, record the run ID and confirm that
the selected object-storage prefix and PostgreSQL database are dedicated to the pilot.

Then use a different empty local workspace/cache:

```bash
export PYINGEST_WORKSPACE=.pyingest-recovery
```

Replay the recorded historical run using the same durable backends:

```bash
pyingest replay <run-id> \
  --config examples/plugin_package/demo-versioned-s3.yml
```

Expected properties:

- historical RAW is materialized from durable object storage;
- no live source acquisition is required;
- the replay fingerprint matches the historical/published dataset as required by strict replay;
- target idempotency prevents an unintended duplicate load where the policy resolves to SKIP;
- the fresh local cache is an implementation aid, not the system of record.

The repository CI performs the destructive workspace-A / fresh-workspace-B form of this scenario in
`tests/integration/test_versioned_s3_e2e.py`.

## 7. PostgreSQL-only pilot

If object storage is not yet available, qualify relational persistence independently:

```bash
pyingest run demo.versioned_postgres \
  --config examples/plugin_package/demo-versioned-postgres.yml \
  --param revision=1
```

The `postgres-e2e` CI tier covers COPY loading, metadata persistence, load modes, idempotency and the
versioned PostgreSQL slice against PostgreSQL 16.

## 8. Operational pre-flight checklist

Before running a real pilot dataset, verify:

- `pyingest config` reports the expected config origin and backends;
- the job's `requires_artifacts` / `requires_metadata` requirements match the selected profile;
- object-storage bucket/prefix is dedicated and writable;
- PostgreSQL metadata and target DSNs point to the intended environment;
- credentials come from environment/provider chains, not YAML;
- the runtime workspace has enough local cache capacity for parser materialization;
- retention/backup rules exist for durable PostgreSQL and object storage;
- the external scheduler invokes one PyIngestKit run at the desired time rather than embedding
  scheduling logic into the job;
- logs are collected from stderr/file JSON without treating logs as authoritative run metadata.

## 9. Failure and recovery expectations

A production-like pilot should explicitly test controlled failure boundaries:

- invalid configuration fails before execution;
- a broken unrelated plugin does not hide healthy jobs in CLI registry loading;
- failed runs/steps remain persisted for diagnosis;
- RAW is immutable;
- replay never silently falls back to live acquisition when historical RAW is missing or mismatched;
- secret-looking values are redacted at logging/CLI failure boundaries.

## 10. What remains external

PyIngestKit does not provision PostgreSQL, buckets, IAM, TLS, VPCs, Kubernetes, Airflow/Dagster/Prefect
or secret managers. The framework owns the ingestion execution contract; the deployment platform owns
those concerns.

See `docs/reference/pilots-v1.md` for the B2 evidence matrix and
`docs/architecture/product-scope-v1.md` for the stable product boundary.
