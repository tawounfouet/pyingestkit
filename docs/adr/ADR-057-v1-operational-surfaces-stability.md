# ADR-057 — V1 operational surfaces are frozen by explicit behavioral contracts

Status: Accepted for **V1.0.0-b1 — Plugin / Config / Error / CLI / Observability Stability**.

## Context

A1 inventoried intentional public surfaces and A2 made model, extension and persistence compatibility
release-blocking. Five user-facing areas were deliberately left unfinished: plugins, configuration,
errors, CLI behavior and observability.

Those surfaces are especially prone to accidental compatibility drift because they include entry
point discovery order, environment precedence, generated CLI options, exception import paths and
logging presentation details.

## Decision

### 1. Freeze external plugin discovery semantics

`pyingestkit.jobs` remains the job-pack entry-point group. Discovery is deterministic, broken plugins
are isolated, duplicate logical job IDs are explicit failures, `discover_jobs()` is strict by default
and CLI registry helpers are tolerant.

### 2. Make configuration selectors fail closed

`PYINGEST_CONFIG` and `PYINGEST_ENV` are explicit selectors. A missing selected file/profile is an
error instead of permission to silently fall through to another environment.

`PYINGEST_WORKSPACE` becomes an implemented stable override. Dotenv loading is cwd-scoped and never
auto-loads `.example` templates.

### 3. Add a canonical error namespace without replacing identities

`pyingestkit.errors` re-exports the existing controlled exception classes. Historical import paths
remain valid and class identity is preserved.

### 4. Standardize visible deprecations

Public V1 deprecations use `PyIngestKitDeprecationWarning(FutureWarning)` via `warn_deprecated`.
Stable public 1.x paths are retained until a later breaking major release.

### 5. Freeze CLI semantics, not terminal pixels

Command names, option aliases, positional argument names and exit-code classes are compatibility
contracts. Rich color, wrapping and whitespace are presentation details.

Generated completion-management options are disabled because they were framework-generated rather
than deliberately designed product surface.

### 6. Freeze logging semantics

Standard-library logging remains the plugin/framework contract. Human logs use local timestamps and
short run IDs; structured JSON uses UTC ISO-8601 timestamps and full IDs. File logging supports only
`plain` and `json`. Secret redaction covers messages, exceptions and URL credentials.

### 7. Add a release-blocking B1 gate

`tests/contract/fixtures/stability_v1.json` and `scripts/check_v1_stability.py` encode the B1 contract.
The gate is part of `make check` and therefore `make release-check`.

## Consequences

Positive:

- plugin installation order no longer affects duplicate behavior;
- explicit environment selection cannot silently execute against another profile;
- users gain one canonical exception namespace without migration breakage;
- generated CLI options cannot expand unnoticed;
- machine/human CLI semantics and exit codes are reviewable;
- logging remains framework-neutral and collector-friendly;
- secrets receive stronger redaction coverage;
- B1 drift blocks release qualification automatically.

Costs:

- a missing `PYINGEST_ENV` profile now fails rather than falling back;
- `.env.*.example` files must be copied to real dotenv files before use;
- `rich` is no longer accepted as a file-log format;
- intentional CLI/config/plugin changes require a governed contract update.

## Alternatives rejected

### Keep plugin discovery order unspecified

Rejected because duplicate outcomes would vary by environment/package installation order.

### Keep configuration fallback permissive

Rejected because silent prod/staging/dev profile substitution is operationally unsafe.

### Create new exception classes under `pyingestkit.errors`

Rejected because it would break identity-based exception handling. Aliasing existing classes provides
better ergonomics without compatibility loss.

### Freeze exact Rich output bytes

Rejected because terminal width, Rich versions and accessibility/presentation choices should not make
semantic CLI compatibility brittle.

### Use `DeprecationWarning`

Rejected for public migration guidance because Python hides it by default for ordinary user code.

## Follow-up

V1.0.0-b2 validates these contracts through real pilot integrations and completes user-facing V1
documentation. RC1 then performs final release/upgrade/security qualification before the stable
`v1.0.0` tag is created.
