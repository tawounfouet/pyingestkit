# PyIngestKit V1 — Representative Pilot Qualification

Status: **V1.0.0-b2 — Real Pilots + Documentation**

B2 does not add a new ingestion provider or orchestration capability. It qualifies the existing V1
framework through representative operator journeys and makes the evidence explicit.

The machine-readable source of truth is `tests/contract/fixtures/pilots_v1.json`, enforced by
`scripts/check_v1_pilots.py` and by the `v1-pilot-gate` CI job.

## 1. Baseline

B2 starts from the sealed B1 merge commit:

```text
9dc4dcfc8363937f4d7653292cce411f559fbf69
```

A1 public API, A2 compatibility and B1 operational-stability gates remain active. B2 adds pilot
qualification; it does not replace an earlier contract.

## 2. Qualification model

A B2 pilot is a representative end-to-end use case built entirely from existing public V1 surfaces.
Each pilot must name:

- the reference job(s) that exercise the use case;
- the executable configuration file(s);
- whether it is fully offline or requires service-backed CI;
- the capabilities under qualification;
- the test files that provide executable evidence;
- the CI job responsible for service-backed evidence where applicable.

B2 deliberately distinguishes a **pilot** from a production deployment. A pilot proves the framework
contract against a representative topology; deployment-specific IAM, networking, scheduling and
infrastructure provisioning remain consumer responsibilities.

## 3. Pilot P1 — Local plugin operator

**Goal:** prove the smallest installable job-pack journey used by a developer or local operator.

```text
plugin package
  -> entry-point discovery
  -> demo.local_file
  -> local immutable RAW
  -> SQLite metadata
  -> run history / status
```

Configuration:

```text
examples/plugin_package/demo.yml
```

Primary evidence:

```text
examples/plugin_package/tests/test_demo_job.py
tests/integration/test_cli_run_history.py
```

This pilot qualifies plugin installation/discovery, a normal CLI-triggered ingestion shape, local
artifact persistence, SQLite metadata and operator history/status semantics.

## 4. Pilot P2 — HTTP acquisition + quality formats

**Goal:** prove acquisition, parsing, validation and profiling across the supported structured formats
without depending on public internet availability.

Reference jobs:

```text
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

Configurations:

```text
examples/plugin_package/demo-http.yml
examples/plugin_package/demo-quality.yml
```

The HTTP jobs use deterministic fixture transports. Excel and Parquet pilots use generated fixtures,
so the qualification is reproducible and network-independent.

Primary evidence:

```text
examples/plugin_package/tests/test_http_jobs.py
examples/plugin_package/tests/test_quality_format_jobs.py
tests/integration/test_http_raw_provenance.py
tests/integration/test_quality_reports_runtime.py
```

This pilot qualifies HTTP-source semantics, retry policy, immutable RAW provenance, parsers,
`DatasetContract`, validation, profiling and materialized quality reports.

## 5. Pilot P3 — Local versioning + strict replay

**Goal:** prove that a dataset can evolve through two revisions, publish a new version, emit a diff and
replay from historical RAW without reacquiring the source.

Reference job:

```text
demo.versioned_ndjson
```

Configuration:

```text
examples/plugin_package/demo-versioned.yml
```

The executable journey is:

```text
revision 1
  -> fingerprint
  -> DatasetVersion V1
  -> publish V1

revision 2
  -> fingerprint
  -> diff(V1, V2)
  -> DatasetVersion V2
  -> publish V2
  -> strict replay of historical run
  -> fingerprint match
```

Primary evidence:

```text
tests/integration/test_versioned_ndjson_e2e.py
tests/integration/test_replay_runtime.py
```

This pilot qualifies fingerprints, diff, immutable versions, publication and strict replay with local
artifact/version storage and SQLite metadata.

## 6. Pilot P4 — PostgreSQL production slice

**Goal:** qualify the relational persistence and target-loading path against a real PostgreSQL service.

Reference job:

```text
demo.versioned_postgres
```

Configuration:

```text
examples/plugin_package/demo-versioned-postgres.yml
```

This is a service-backed CI pilot. The required job is:

```text
postgres-e2e
```

Primary evidence:

```text
tests/integration/test_postgres_target_copy.py
tests/integration/test_postgres_metadata_target_loads.py
tests/integration/test_postgres_load_modes_idempotency.py
tests/integration/test_versioned_postgres_e2e.py
```

It qualifies PostgreSQL metadata, PostgreSQL targets, COPY-based loading, transactional replacement,
load modes, target-load lineage and idempotency.

## 7. Pilot P5 — Cross-host object-storage recovery

**Goal:** qualify the production-like topology where local workspace state is disposable and durable
state lives in PostgreSQL plus S3-compatible object storage.

Reference job:

```text
demo.versioned_s3
```

Configuration:

```text
examples/plugin_package/demo-versioned-s3.yml
```

Required CI job:

```text
object-storage-e2e
```

The representative journey is:

```text
host/workspace A
  -> revision 1
  -> revision 2
  -> remote RAW/reports/manifests
  -> remote DatasetVersion snapshots
  -> published pointer
  -> PostgreSQL metadata + target

DESTROY local workspace A

fresh host/workspace B
  -> resolve historical durable RAW
  -> strict replay
  -> fingerprint match
  -> idempotent target decision
```

Primary evidence:

```text
tests/integration/test_versioned_s3_e2e.py
tests/integration/test_s3_remote_raw.py
tests/integration/test_s3_dataset_versions.py
```

The CI service uses pinned MinIO as an S3-compatible implementation and PostgreSQL 16. The contract is
S3-compatible rather than MinIO-specific.

## 8. Pilot coverage matrix

| Pilot | Source | Formats / quality | Metadata | Artifact/version storage | Target | Replay | CI class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 Local operator | Local file | RAW | SQLite | Filesystem | — | — | Offline |
| P2 HTTP + quality | HTTP fixtures | CSV/JSON/NDJSON/Excel/Parquet + validation/profile | SQLite | Filesystem | — | — | Offline |
| P3 Local versioning | HTTP fixture | NDJSON + validation/profile | SQLite | Filesystem | — | Strict | Offline |
| P4 PostgreSQL | Fixture source | Versioned dataset | PostgreSQL / SQLite variants | Filesystem | PostgreSQL | Covered by versioned slice | Service-backed |
| P5 Cross-host | Fixture source | Versioned dataset | PostgreSQL | S3-compatible | PostgreSQL | Strict, fresh workspace | Service-backed |

Together these pilots exercise all nine maintained reference jobs. They intentionally do not pretend
to cover every possible user source, schema or cloud provider.

## 9. B2 documentation acceptance criteria

B2 is not complete merely because tests pass. The following user journeys must also be documented:

1. install and run a first job;
2. understand config/profile/workspace precedence;
3. package/discover an external job plugin;
4. operate a production-like PostgreSQL + S3-compatible pilot;
5. inspect history, versions and publication;
6. replay safely from historical RAW;
7. migrate from the V0.6 stable baseline to the V1 contract candidate;
8. understand which surfaces are stable, experimental or internal.

The B2 manifest lists the required documents, and the machine gate fails if one disappears.

## 10. Release-blocking CI semantics

B2 introduces `v1-pilot-gate`. It depends on the normal Python matrix plus PostgreSQL, S3,
cross-host object-storage and foundation qualification. Therefore the aggregate pilot gate can only be
green if its executable evidence has already passed.

The pilot gate then validates the manifest itself: every reference job must be covered, every entry
point/config/evidence file must exist, every service-backed pilot must name an explicit CI job, and all
required V1 user documentation must exist.

## 11. What B2 does not claim

B2 does not create `v1.0.0`, does not publish a release candidate and does not freeze release assets.
It also does not add scheduling, distributed orchestration, IAM, secret storage or cloud provisioning.

Those boundaries remain intentional.

Next milestone:

- **V1.0.0-rc1** — full release/upgrade/security E2E, candidate packaging and final release-readiness
  qualification before the stable version bump/tag.
