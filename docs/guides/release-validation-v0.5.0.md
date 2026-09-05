# PyIngestKit V0.5.0 — Release Validation

V0.5.0 is accepted only when one stable commit passes the complete release line without functional changes after RC1.

## Required gates

```bash
make check
make quality
make security
make build
make wheel-smoke
```

The GitHub Actions matrix also qualifies Python 3.11, 3.12 and 3.13.

## Real PostgreSQL gate

A PostgreSQL 16 service executes the persistence integration suite:

```text
tests/integration/test_postgres_target_copy.py
tests/integration/test_postgres_metadata_target_loads.py
tests/integration/test_postgres_load_modes_idempotency.py
tests/integration/test_versioned_postgres_e2e.py
```

This preserves regression evidence for:

- A2 schema mapping and psycopg COPY;
- B1 target-load metadata;
- B2 transactional load modes and idempotency;
- RC1 V1/V2/diff/version/publish/replay E2E.

## Packaging gate

`make build` produces the framework wheel/sdist and the demo-job wheel/sdist. `make wheel-smoke` creates a fresh virtual environment, installs the produced wheels with real Excel, Parquet and PostgreSQL extras, validates package version `0.5.0`, discovers all eight entry points and executes the non-PostgreSQL reference suite including strict RAW replay.

The PostgreSQL reference job is executed in the dedicated service-backed integration job rather than the service-free wheel-smoke job.

## Compatibility matrix

```text
Python                  3.11 / 3.12 / 3.13
Metadata                Memory / SQLite / PostgreSQL
PostgreSQL target       PostgreSQL 16 real service
Excel extra             OpenPyXL
Parquet extra           PyArrow
PostgreSQL extra        psycopg 3
```

## Stable promotion rule

The stable commit may change version strings, documentation, changelog, CI/release metadata and packaging evidence only. It must not introduce a new runtime feature after RC1 qualification.

After merge to `main`, the merge commit must pass the same required checks before the immutable `v0.5.0` tag is created.
