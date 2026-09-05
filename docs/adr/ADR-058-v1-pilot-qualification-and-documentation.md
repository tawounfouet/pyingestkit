# ADR-058 — V1 readiness is demonstrated by representative pilots and executable documentation contracts

Status: Accepted for **V1.0.0-b2 — Real Pilots + Documentation**.

## Context

A1 froze the intended public Python surface, A2 made compatibility and persisted logical contracts
release-blocking, and B1 stabilized plugin/config/error/CLI/observability behavior.

Those contracts can still look correct in isolation while failing to describe how a real operator
combines them. PyIngestKit already owns executable reference jobs spanning local files, HTTP, quality
formats, versioning, PostgreSQL and S3-compatible object storage. The missing B2 work is therefore not
another provider: it is a governed proof that representative end-to-end journeys remain executable and
understandable.

## Decision

### 1. Qualify existing capabilities instead of expanding scope

B2 introduces no new ingestion provider and no orchestration platform. The maintained nine-job demo
pack is the representative V1 evidence set.

### 2. Define five representative pilots

B2 groups the existing executable evidence into:

1. local plugin operator;
2. HTTP acquisition + quality formats;
3. local versioning/diff/publish/strict replay;
4. PostgreSQL production slice;
5. cross-host PostgreSQL + S3-compatible recovery/replay.

The first three are reproducible offline. The last two require service-backed CI.

### 3. Keep pilot evidence machine-readable

`tests/contract/fixtures/pilots_v1.json` records pilot IDs, job/entry-point coverage, configs,
capabilities, evidence files, required CI tiers and required documentation.

`scripts/check_v1_pilots.py` rejects drift such as:

- a maintained reference job not covered by a pilot;
- a pilot referencing a missing entry point, config or evidence file;
- a service-backed pilot without an explicit CI tier;
- removal of required V1 user documentation;
- accidental B2 scope expansion.

### 4. Make the aggregate pilot gate release-blocking

CI adds `v1-pilot-gate`, dependent on the Python matrix, PostgreSQL E2E, S3 E2E, cross-host object
storage E2E and foundation/release-check tiers.

The aggregate gate does not duplicate every test. Its dependency graph means executable evidence must
already have succeeded; it then validates the B2 pilot/documentation manifest.

### 5. Treat documentation as part of release qualification

B2 requires user-facing documentation for:

- first install/run;
- configuration and workspace precedence;
- plugin behavior;
- production-like PostgreSQL + S3-compatible operation;
- run/version/publication inspection;
- replay;
- V0.6-to-V1 migration;
- public/stable/experimental/internal boundaries.

Documentation paths are part of the B2 machine manifest so they cannot disappear silently.

### 6. Do not confuse pilots with production certification

A B2 pilot proves framework behavior against a representative topology. It does not certify a user's
IAM, networking, scheduler, secret manager, backup policy or cloud infrastructure.

## Consequences

Positive:

- V1 readiness is evidenced by end-to-end journeys rather than isolated unit contracts;
- all nine maintained reference jobs have an explicit qualification role;
- service-backed evidence is aggregated into one reviewable gate;
- documentation completeness becomes machine-governed;
- the framework boundary remains focused and no late feature expansion is introduced.

Costs:

- changing or removing a reference job requires deliberate pilot-contract review;
- CI gains one aggregate dependency gate;
- documentation moves become governed changes rather than untracked refactors.

## Alternatives rejected

### Add more providers to make B2 look more production-like

Rejected. Provider expansion would increase V1 risk and contradict the frozen roadmap. Existing local,
HTTP, PostgreSQL and S3-compatible slices are sufficient to qualify the framework contract.

### Call every integration test a pilot

Rejected. A pilot is a user-oriented representative journey with an explicit topology and capability
purpose, not merely a test file.

### Depend only on documentation prose

Rejected. B2 claims must remain executable and tied to CI evidence.

### Duplicate all service-backed tests inside one giant pilot job

Rejected. It would increase CI duration and maintenance while providing no additional evidence. The
aggregate gate depends on the existing specialized jobs instead.

## Follow-up

V1.0.0-rc1 consumes the sealed B2 pilot evidence and performs final release/upgrade/security E2E plus
release-candidate packaging. Only after RC1 and final stable qualification may the immutable
`v1.0.0` tag/release be created.
