# ADR-059 — V1 RC1 is a real package candidate and must upgrade the immutable V0.6 baseline

Status: Accepted for **V1.0.0-rc1 — Full Stability Candidate**.

## Context

A1 froze the public API scope, A2 made compatibility and persisted logical contracts executable, B1
froze operational behavior, and B2 qualified representative end-to-end pilots plus user documentation.

The remaining risk before a stable 1.0.0 release is release engineering itself. A source tree can pass
all functional tests while the built distribution is mis-versioned, its demo package still depends on a
pre-V1 range, CI publishes misleading artifact names, or a real V0.6 workspace cannot be consumed after
installing the V1 candidate.

## Decision

### 1. RC1 uses a real PEP 440 candidate version

The framework and maintained demo distribution are built as:

```text
1.0.0rc1
```

The stable target remains `1.0.0`. RC1 does not create or imply the stable `v1.0.0` tag.

### 2. Distribution compatibility is qualified from built wheels

The clean-wheel smoke test installs the framework and demo wheels into a fresh virtual environment,
checks the public version and imports, discovers all nine maintained entry points, runs the offline
representative jobs, validates version/diff/publication behavior, and performs strict replay.

This prevents editable-install success from being mistaken for release-package success.

### 3. V0.6.0 is the explicit upgrade baseline

The immutable `v0.6.0` tag is treated as release evidence. The RC upgrade smoke test:

1. checks out the exact `v0.6.0` tag in a detached worktree;
2. installs the historical framework and demo package into a clean environment;
3. creates real V0.6 versioned run history, snapshots and publication state;
4. upgrades that same environment to the built `1.0.0rc1` wheels;
5. proves the historical run remains readable;
6. proves DatasetVersion history and PublishedDataset remain readable;
7. performs strict replay from the historical RAW and requires fingerprint equality.

No Git history is rewritten and the historical `v0.6.0` tag remains immutable.

### 4. Release metadata and CI names must agree

RC1 adds a machine-readable release-candidate manifest and gate. It checks that framework version,
demo package version/dependency range, wheel-smoke constants, documentation, CI job names and CI
artifact names all agree on `1.0.0rc1`.

V0.6-named CI artifact uploads are forbidden on the RC branch because they would misrepresent the
candidate distributions.

### 5. RC1 remains cumulative

The RC gate is additive. It does not replace A1/A2/B1/B2 qualification. The aggregate release gate must
still depend on:

- Python 3.11/3.12/3.13 checks;
- PostgreSQL E2E;
- S3 E2E;
- full cross-host object-storage E2E;
- clean build/wheel smoke;
- V0.6 -> V1 upgrade smoke;
- B2 pilot gate;
- RC1 release-candidate contract gate.

### 6. RC1 adds no product scope

No new provider, orchestration platform, persistence model or public feature is introduced in RC1.
Changes are limited to release metadata, package qualification, upgrade evidence, security and release
documentation.

## Consequences

Positive:

- the candidate version printed by the CLI is the version contained in the wheel;
- the demo distribution is installable against the candidate rather than the old `<0.7` range;
- CI artifacts are unambiguous and reviewable;
- V0.6 persisted state is exercised through an actual package upgrade rather than only static schema
  assertions;
- the stable `v1.0.0` tag remains unavailable until final stable qualification.

Costs:

- RC release-check requires access to repository history and the immutable `v0.6.0` tag;
- release-check takes longer because it performs a second isolated installation/upgrade journey;
- changing candidate version metadata requires coordinated updates across governed release artifacts.

## Follow-up

After RC1 is merged and the exact merge SHA passes post-merge CI and Security, the stable milestone may
replace `1.0.0rc1` with `1.0.0`, repeat the complete release qualification, create an annotated immutable
`v1.0.0` tag on the qualified stable SHA, and publish the final distributions plus checksums.
