# Security Policy

PyIngestKit V0.6.0 treats credentials, durable ingestion artifacts, and operational metadata as separate security domains.

## Stable security invariants

- secrets are never artifacts and must not be serialized into manifests, reports, DatasetVersion metadata, PublishedDataset pointers, replay records, logs, or exception representations;
- project YAML stores environment-variable names and non-secret connection settings, not PostgreSQL DSNs or S3 access keys;
- S3 credentials are resolved through the standard boto3/AWS credential provider chain;
- importing `pyingestkit` does not create files, open network/database connections, or discover plugins;
- optional providers remain optional: importing the core does not require boto3, psycopg, OpenPyXL, or PyArrow;
- RAW and DatasetVersion objects are immutable at the PyIngestKit contract level and retain explicit SHA-256 integrity metadata;
- replay never silently falls back to the original source when the required historical artifact is missing or corrupt.

## Object-storage production guidance

Production buckets should be private. Grant the runner only the bucket/prefix permissions required by its job and environment; prefer workload identity, IAM roles, OIDC/web identity, or equivalent short-lived credentials over static long-lived keys.

Use TLS for remote object storage. Plain HTTP endpoints are acceptable only for controlled local/CI MinIO environments. Server-side encryption can be configured through the storage provider where required; PyIngestKit does not manage KMS keys or IAM policy.

Retention policies must preserve every RAW object and DatasetVersion snapshot required for replay, lineage, or audit. Do not configure lifecycle expiry that invalidates those guarantees without an explicit retention decision.

## CI / MinIO hygiene

The V0.6.0 stable CI pins the MinIO image by digest and creates fresh random MinIO credentials for each service-backed job. Fixed/default MinIO credentials are prohibited in current workflows. Test credentials are disposable and never represent production secrets.

## Dependency and release security

The release gate includes Bandit and `pip-audit`, plus unit/contract tests, PostgreSQL integration, MinIO/S3 integration, full cross-host replay, clean-wheel installation, and Python 3.11/3.12/3.13 qualification.

Report security issues privately to the project maintainer rather than opening a public issue containing sensitive data.
