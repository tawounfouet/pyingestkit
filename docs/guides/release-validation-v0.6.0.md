# V0.6.0 stable release validation

This guide is the operational qualification checklist for PyIngestKit V0.6.0.

## Local release gate

```bash
python -m pip install -e ".[dev,excel,parquet,postgres,s3]"
python -m pip install -e examples/plugin_package
make release-check
```

`make release-check` covers tests, demo tests, public API freeze, bytecode compilation, Ruff lint/format, Mypy strict, Bandit, `pip-audit`, wheel/sdist builds, and isolated clean-wheel installation.

## Required service-backed CI tiers

The stable GitHub workflow additionally requires:

```text
Python 3.11 / 3.12 / 3.13
PostgreSQL 16 target/metadata regressions
MinIO S3 remote RAW + version-store regressions
PostgreSQL + MinIO full cross-host replay E2E
stable release-check
stable-release-gate
```

The cross-host test must prove V1/V2 remote RAW, remote reports/diff, immutable snapshots, PublishedDataset V2, deletion of workspace A, replay from workspace B without live source acquisition, fingerprint equality, and idempotent PostgreSQL `SKIP`.

## Security qualification

- MinIO image is pinned by digest.
- CI MinIO credentials are randomly generated per job.
- current workflow contains no fixed/default MinIO password.
- project-owned Security workflow (`Bandit` + `pip-audit`) is green.
- no credentials are serialized into config, manifests, reports, snapshot metadata, or release notes.

An external secret scanner can continue to report a historical disposable test credential from an earlier V0.6 commit. The repository history is intentionally not rewritten because milestone SHAs A1→RC1 are release evidence. That historical scanner finding should be reviewed/dismissed as a test-credential false positive in the scanner UI; the current stable workflow must remain clean.

## Promotion sequence

```text
qualified stable branch HEAD
        ↓
merge PR #10 with merge commit (no squash)
        ↓
main CI + Security green
        ↓
tag v0.6.0
        ↓
GitHub Release v0.6.0
        ↓
publish wheel / sdist / source ZIP / SHA256SUMS
```

## Final checksums

`SHA256SUMS` is generated from framework and demo distribution artifacts. The source ZIP receives its own SHA-256 when downloaded from the stable CI artifact.
