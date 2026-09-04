# PyIngestKit V0.4.0 stable release validation

## Purpose

This guide defines the acceptance procedure for **V0.4.0 — Diff / Replay / Versioning Release**. Stable is a promotion of the qualified RC1 behavior after hardening; it introduces no new runtime feature.

## Frozen stable contracts

V0.4.0 freezes:

```text
public top-level API names             scripts/check_public_api.py
CLI commands                           jobs / inspect / run / runs / status / versions / published / replay
Dataset fingerprint canonical codec    1
Dataset snapshot_version               "1"
Diff report_version                    "1"
```

Any incompatible future serialization/report change requires a new explicit format version.

## Prerequisites

- Python 3.11, 3.12 and 3.13 remain supported by CI;
- the `excel` extra resolves OpenPyXL;
- the `parquet` extra resolves real PyArrow;
- the demo package exposes exactly seven `pyingestkit.jobs` entry points;
- no production secret is required by the reference suite.

## Aggregate release gate

From the repository root:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e examples/plugin_package
make release-check
```

`make release-check` must succeed completely. It includes source tests/contracts, Ruff, formatting, Mypy strict mode, Bandit, `pip-audit`, framework/demo package builds and the clean-wheel smoke test.

## Distribution smoke proof

The wheel-smoke gate creates a fresh virtual environment and installs the built framework wheel with `excel` and `parquet` extras plus the built demo wheel. It must prove:

1. `import pyingestkit`, `openpyxl` and `pyarrow` succeed;
2. `pyingestkit.__version__ == "0.4.0"`;
3. exactly seven reference jobs are discovered;
4. the six pre-V0.4 reference jobs execute successfully;
5. `demo.versioned_ndjson` revision 1 succeeds and publishes V1;
6. revision 2 succeeds, creates `reports/diff.json`, creates V2 and publishes V2;
7. the V1/V2 diff summary is exactly `added=1`, `removed=1`, `changed=1`, `unchanged=1`;
8. exactly two content-addressed versions exist before replay;
9. `PublishedDataset` points to the revision-2 run;
10. replay of revision 2 succeeds in `STRICT` mode using historical RAW;
11. replay `expected_fingerprint` and `actual_fingerprint` equal the published V2 fingerprint;
12. replay manifest lineage records the original revision-2 run.

The reference replay path uses a network-forbidden client; a successful run therefore proves that historical RAW was resolved before any live transport call.

## Metadata compatibility

Release qualification must retain:

- additive SQLite V0.4 tables/capabilities;
- PostgreSQL adapter contract coverage;
- execution with a legacy/custom MetadataStore that does not implement optional diff/version capabilities;
- the V0.1-V0.3 public contracts covered by the existing test suite.

## CI and security acceptance

The release SHA is accepted only when:

```text
CI / Python 3.11       PASS
CI / Python 3.12       PASS
CI / Python 3.13       PASS
CI / release-check     PASS
Security               PASS
```

Do not merge/tag a SHA that has not received those checks.

## Build outputs

Expected distribution files:

```text
dist/pyingestkit-0.4.0.tar.gz
dist/pyingestkit-0.4.0-py3-none-any.whl
examples/plugin_package/dist/pyingestkit_demo_jobs-0.4.0.tar.gz
examples/plugin_package/dist/pyingestkit_demo_jobs-0.4.0-py3-none-any.whl
```

Expected source delivery archive:

```text
pyingestkit-v0.4.0.zip
```

Record SHA-256 checksums for the final delivery artifacts before publication.
