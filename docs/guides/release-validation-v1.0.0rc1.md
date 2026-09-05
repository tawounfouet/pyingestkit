# V1.0.0rc1 release candidate validation

This guide defines the release-blocking qualification for **PyIngestKit 1.0.0rc1**. RC1 is a real
PEP 440 package candidate, not the final stable release. The immutable `v0.6.0` release remains the
historical upgrade baseline and the stable `v1.0.0` tag must not be created until the final stable
qualification has passed.

## Candidate identity

Expected framework version:

```text
1.0.0rc1
```

Expected maintained demo package version:

```text
1.0.0rc1
```

Expected demo dependency range:

```text
pyingestkit>=1.0.0rc1,<1.1
```

Expected build artifacts:

```text
pyingestkit-1.0.0rc1-py3-none-any.whl
pyingestkit-1.0.0rc1.tar.gz
pyingestkit_demo_jobs-1.0.0rc1-py3-none-any.whl
pyingestkit_demo_jobs-1.0.0rc1.tar.gz
SHA256SUMS
```

## Local qualification

From a clone that contains the immutable `v0.6.0` tag:

```bash
make release-check
```

The command is cumulative and must complete all of the following:

```text
unit + contract + integration tests
        ↓
A1 public API gate
        ↓
A2 compatibility gate
        ↓
B1 operational stability gate
        ↓
B2 representative pilot/documentation gate
        ↓
RC1 package/release metadata gate
        ↓
Ruff + formatting + Mypy
        ↓
Bandit + pip-audit
        ↓
wheel + sdist build
        ↓
clean-wheel installation smoke
        ↓
V0.6.0 -> 1.0.0rc1 upgrade smoke
```

## Clean-wheel smoke

`scripts/wheel_smoke_test.py` creates a fresh virtual environment and installs only the built candidate
wheels plus declared dependencies. It must prove:

- `pyingest --version` reports `1.0.0rc1`;
- the framework imports from the installed environment rather than the source tree;
- all nine maintained `pyingestkit.jobs` entry points are discovered;
- local, HTTP and quality-format reference jobs run successfully;
- the local versioned reference produces V1/V2 versions, diff and publication state;
- strict replay succeeds and records correct lineage/fingerprint equality.

The PostgreSQL and S3 service-backed paths are intentionally kept in their dedicated CI jobs.

## V0.6 -> V1 upgrade smoke

`scripts/upgrade_smoke_test.py` is the executable upgrade contract. It requires repository history with
the immutable `v0.6.0` tag available.

The script:

1. creates a detached worktree at `v0.6.0`;
2. installs the V0.6 framework and historical demo package into a clean virtual environment;
3. creates two real `demo.versioned_ndjson` runs and persisted V0.6 history/version/publication state;
4. upgrades the same environment to the built `1.0.0rc1` framework and demo wheels;
5. verifies the historical successful run remains readable;
6. verifies both content-addressed DatasetVersion snapshots remain readable;
7. verifies the existing PublishedDataset still points at the historical V2 run;
8. strict-replays the historical V2 RAW under RC1 and requires fingerprint equality.

This test deliberately uses the release tag instead of a recreated fixture so the upgrade evidence is
anchored to the real immutable V0.6 release lineage.

## CI qualification

The RC1 PR and the eventual RC1 merge commit must pass:

```text
test (Python 3.11)
test (Python 3.12)
test (Python 3.13)
postgres-e2e
s3-e2e
object-storage-e2e
foundation-verify
v1-pilot-gate
v1-rc-gate
stable-release-gate
Security / audit
```

`foundation-verify` checks out full history/tags because the upgrade smoke consumes `v0.6.0`.

The service-backed tiers retain the already qualified PostgreSQL 16 and pinned MinIO topology. RC1
must not add a provider merely to expand the release matrix.

## CI artifacts

The candidate CI artifacts are named:

```text
pyingestkit-v1.0.0rc1-source
pyingestkit-v1.0.0rc1-dist
```

The distribution artifact contains framework wheel/sdist, demo wheel/sdist and `SHA256SUMS`.

V0.6-named artifact uploads are not valid for RC1. The historical V0.6 release assets remain immutable
and separate.

## Security gate

`make security` remains release-blocking:

```text
Bandit
pip-audit
```

The Security workflow must pass on the exact candidate PR head and again on the exact merge commit.
Historical test credentials already classified as test credentials are not a reason to rewrite release
history.

## Merge policy

RC1 uses the same protected release discipline as previous milestones:

```text
qualified branch head
        ↓
PR green + Security green
        ↓
merge commit (no squash, no rebase)
        ↓
post-merge qualification on exact main SHA
```

Only after the post-merge RC1 baseline is sealed may the stable `1.0.0` release branch/commit replace
candidate version metadata with `1.0.0` and rerun the entire release-check.

## What RC1 does not do

RC1 does **not**:

- create the stable `v1.0.0` tag;
- publish a stable `1.0.0` release;
- move or redefine `v0.6.0`;
- introduce a new ingestion provider;
- introduce an orchestration platform;
- change persisted schema versions merely for the package version transition.
