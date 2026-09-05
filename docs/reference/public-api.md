# PyIngestKit V1 — Public API Reference and A1 Classification

Status: **Created in V1.0.0-a1; reviewed through V1.0.0-b1**

This document is the human-readable companion to the machine-readable snapshot at
`tests/contract/fixtures/public_api_v1.json`.

The A1 question is deliberately narrow:

> Which PyIngestKit surfaces are intentionally public, and which of them are candidates for a
> compatibility promise across the future 1.x line?

A1 established the inventory. A2 consolidated structural/persistent compatibility, and B1 finalized
plugin/config/error/CLI/observability stability. This document now reflects those later promotions while
retaining the A1 inventory history.

## 1. Baseline

The qualified Pre-A1 code baseline is:

```text
81f6e5fd2f56698194f08b6a2dd026ab0fff454e
```

The A1 feature branch was initialized from `22537309340146bf72e1d375484a6557e2758a2d`.
That commit has the same tree SHA as the qualified baseline:

```text
e70ef228ff0dac2e7318382073f61caead2aaba5
```

The difference is only a no-op probe create/revert pair in Git history; the source tree used for
this audit is byte-identical to the qualified Pre-A1 tree.

## 2. Classification vocabulary

Every inventoried public symbol belongs to one of these categories:

- `PUBLIC_STABLE_CANDIDATE`: intended to enter the 1.x compatibility contract unless a later V1
  review finds a concrete reason to amend it before RC1.
- `PUBLIC_EXPERIMENTAL`: intentionally importable/documented today, but not yet promised stable
  across 1.x. Any promotion or redesign must be explicit and update the snapshot.
- `INTERNAL`: implementation detail. Importability does not create a compatibility promise.
- `DEPRECATED`: supported temporarily with an explicit replacement/removal path.
- `REMOVE_BEFORE_V1`: accidental or unsuitable surface that must not survive the V1 freeze.

At A1 there are no symbols intentionally marked `DEPRECATED` or `REMOVE_BEFORE_V1`. Accidental
or ambiguous exports discovered by the audit are instead documented below and classified
`PUBLIC_EXPERIMENTAL` where they are already intentionally exposed by a package `__all__`.

## 3. Canonical import rule

The preferred API is the top-level package for common job-authoring contracts:

```python
from pyingestkit import Dataset, Job, Pipeline, RunContext, Step
from pyingestkit import job, step
```

Specialized extension contracts may live under explicitly supported namespaces:

```python
from pyingestkit.artifacts import ArtifactStore, LocalArtifactStore
from pyingestkit.parsers import Parser
from pyingestkit.sources import Source
from pyingestkit.sources.http import HttpSource
from pyingestkit.targets import PostgresTarget, Target
```

The rule is **not** "everything below `src/pyingestkit` is public". A module is part of the V1
public inventory only when it is listed in the A1 manifest or explicitly documented as a public
namespace.

## 4. Top-level API

`pyingestkit.__all__` is an exact A1 snapshot of 60 symbols. They are all
`PUBLIC_STABLE_CANDIDATE` because V0.6 already enforced the exact top-level export set.

The surface covers:

- execution: `Job`, `Step`, `Pipeline`, `Runner`, `RunContext`, result/status types;
- declarative authoring: `job`, `step`, definitions and invocations;
- datasets and contracts;
- CSV/JSON/NDJSON/Excel/Parquet parsers;
- validation, profiling and quality reports;
- fingerprinting, diff, versioning, publication and replay;
- target loading/idempotency/PostgreSQL;
- durable artifact and S3-compatible version-store references.

`pyingestkit.__version__` is also a documented public attribute even though it is not in
`__all__`.

The authoritative symbol-by-symbol list is the JSON snapshot, not a duplicated hand-maintained
list in this document.

## 5. Explicitly public namespaces

The following namespaces are inventoried and contract-snapshotted in A1:

| Namespace | A1 classification | Notes |
| --- | --- | --- |
| `pyingestkit` | stable candidate | ergonomic top-level API |
| `pyingestkit.artifacts` | stable candidate | artifact-store extension contract, local + S3-compatible |
| `pyingestkit.config` | stable candidate | B1 freezes precedence, env names and fail-closed selection |
| `pyingestkit.contracts` | stable candidate | dataset/field contracts |
| `pyingestkit.core` | mixed | execution types + `JobRegistry` stable candidate; events/hooks remain experimental |
| `pyingestkit.declarative` | stable candidate | decorators and compiled definitions |
| `pyingestkit.diff` | stable candidate | deterministic dataset diff contract |
| `pyingestkit.errors` | stable candidate | canonical V1 exception namespace; historical identities preserved |
| `pyingestkit.deprecations` | stable candidate | canonical visible deprecation helper/category |
| `pyingestkit.parsers` | stable candidate | parser contract and built-in adapters |
| `pyingestkit.profiling` | stable candidate | descriptive profiling |
| `pyingestkit.publication` | stable candidate | atomic publication abstraction |
| `pyingestkit.quality` | stable candidate | portable quality report |
| `pyingestkit.replay` | mixed | replay models/service stable candidate; materialization helper experimental |
| `pyingestkit.retry` | stable candidate | HTTP retry policy contract |
| `pyingestkit.runtime` | stable candidate | `Runner` |
| `pyingestkit.sources` | stable candidate | source abstraction/local source |
| `pyingestkit.sources.http` | stable candidate | HTTP transport/source contract |
| `pyingestkit.targets` | stable candidate | target/load/error surface |
| `pyingestkit.validation` | stable candidate | rules/results/reports |
| `pyingestkit.versioning` | stable candidate | fingerprint/version/snapshot/publication-store types |
| `pyingestkit.logging` | stable candidate | B1 observability/logging helper contract |
| `pyingestkit.metadata` | mixed | A2 governs logical records/stores; physical SQL layout remains internal |
| `pyingestkit.plugins` | stable candidate | B1 deterministic discovery + isolation contract |
| `pyingestkit.provenance` | mixed | A2 governs `RunManifest` schema v1; low-level helpers remain reviewed separately |
| `pyingestkit.cli` | experimental Python API | console entry point is public; Typer `app` object is not yet a 1.x promise |

For all namespaces above, the exact current `__all__` set is captured in the JSON snapshot and
checked by `tests/contract/test_public_api_v1.py`.

## 6. Exceptions

B1 establishes `pyingestkit.errors` as the canonical V1 exception namespace. It aggregates the
controlled core, HTTP and target error families while preserving historical class identity. Existing
imports from `pyingestkit.core.exceptions`, `pyingestkit.sources.http` and `pyingestkit.targets` remain
compatible aliases, so existing `except` clauses do not need to change.

`IngestionError` remains the base class for controlled ingestion failures. Raw SQLAlchemy, psycopg or
boto3 exceptions are not the intended user contract when PyIngestKit can translate them into a
framework-level error.

Public deprecations use `pyingestkit.deprecations.PyIngestKitDeprecationWarning`, a `FutureWarning`
subclass visible under normal Python warning filters. Stable 1.x APIs are retained until a later
breaking major release.

## 7. Callable/signature audit

A1 reviewed the public families against these compatibility dimensions:

```text
positional vs keyword parameters
default values
optional semantics
return type
controlled exceptions
side effects / persistence
```

Findings:

- `Job.pipeline()` and `Step.execute(...)` are extension points and must remain conservative.
- `ArtifactStore` deliberately keeps URI/materialization additions non-abstract where possible so
  pre-V0.6 third-party stores remain source-compatible.
- `Source`, `Parser`, `Target`, `DatasetVersionStore` and `MetadataStore` are extension boundaries;
  provider implementations must not leak into their core contracts.
- additive keyword-only parameters are preferred to incompatible positional changes.
- exact signature compatibility will receive explicit regression coverage as surfaces graduate
  from candidate/experimental to stable before RC1.

## 8. Model audit

Public Pydantic/dataclass-like models are reviewed for:

```text
field names
required/optional status
defaults
serialization
validation
immutability
forward compatibility
```

Important A1 decisions:

- configuration models use `extra="forbid"` and frozen instances; new keys therefore require an
  intentional schema change;
- metadata record models remain experimental until V1.0.0-a2 audits persistent schemas and upgrade
  behavior;
- snapshot/version/fingerprint models remain public candidates because their deterministic
  behavior is already a core reproducibility contract;
- S3 configuration remains secret-free: credentials belong to the provider/environment chain, not
  YAML models.

## 9. Enum audit

Public enums are compatibility-sensitive. A1 treats existing values as part of the candidate
contract. Adding a new enum value may be source-compatible in Python while still breaking callers
that assume exhaustive matching, so additions must be documented and tested rather than treated as
invisible implementation details.

Relevant families include run/step status, diff kind/policy, target load modes/status/idempotency,
metadata/artifact backend choices, validation severity and log output format.

## 10. CLI inventory

The console entry point is:

```text
pyingest
```

A1 stable-candidate command names are:

```text
config
help
inspect
jobs
published
replay
run
runs
status
versions
```

Root options include `--help`/`-h` and `--version`/`-V`.

A1 snapshotted command names. B1 additionally freezes positional argument names, option aliases and
exit-code classes through `stability_v1.json`. Successful `--json` payload semantics are stable;
errors use stderr plus the canonical `Error:` prefix. Rich styling/wrapping remains presentation, not
a byte-for-byte contract.

## 11. Configuration inventory

Resolution precedence is currently:

```text
explicit --config
  ↓
PYINGEST_CONFIG
  ↓
PYINGEST_ENV -> pyingest.yml.<env>
  ↓
pyingest.yml / pyingestkit.yml / .pyingest.yml
  ↓
in-memory defaults
```

The V1 environment-facing names are:

```text
PYINGEST_CONFIG
PYINGEST_ENV
PYINGEST_WORKSPACE
PYINGEST_DATABASE_URL
PYINGEST_TARGET_DATABASE_URL
PYINGEST_S3_ENDPOINT_URL
```

The root configuration sections are:

```text
runtime
artifacts
metadata
targets
logging
```

B1 finalizes configuration selection as fail closed for explicit environment/profile selectors,
adds the implemented `PYINGEST_WORKSPACE` override, and freezes cwd-scoped dotenv behavior. Files
ending in `.example` are templates only and are never auto-loaded.

## 12. Plugin inventory

The stable-candidate entry-point group is:

```text
pyingestkit.jobs
```

The reference package proves external discovery using installable entry points. B1 freezes accepted
`Job`/`JobDefinition` values plus subclasses/factories, deterministic ordering, duplicate-job-ID
isolation, strict library discovery and tolerant CLI registry loading. The discovery helpers are now
`PUBLIC_STABLE_CANDIDATE`.

## 13. Optional extras

A1 freezes the names and responsibilities of the currently retained extras:

| Extra | Responsibility |
| --- | --- |
| `excel` | Excel parser support through openpyxl |
| `parquet` | Parquet parser support through PyArrow |
| `postgres` | PostgreSQL driver/integration support |
| `s3` | S3-compatible object storage support |
| `dev` | contributor/test/release tooling |

Provider SDKs remain optional: `boto3`, `psycopg`, `openpyxl` and `pyarrow` are not mandatory core
runtime dependencies.

## 14. Base dependency governance

A1 retains the project policy of using established production-grade dependencies when justified;
there is no stdlib-only objective.

Current base families are intentionally reviewed rather than removed mechanically:

```text
Typer / Rich       CLI and human UX
Pydantic / PyYAML  validated configuration/contracts
SQLAlchemy         metadata persistence abstraction
httpx              HTTP transport
tenacity           retry mechanics
python-dotenv      local environment ergonomics
```

Architecture fitness tests protect the important boundary: core/runtime code must not acquire a
direct dependency on optional provider SDKs or orchestration platforms.

## 15. Python support policy draft

The V1 candidate support matrix is:

```text
Python 3.11
Python 3.12
Python 3.13
```

The package metadata and CI matrix must agree. Dropping a supported Python version is a governed
compatibility decision, not an incidental CI edit.

## 16. Accidental/ambiguous surface findings

The audit identified intentionally importable surfaces that should not be silently treated as
already-frozen 1.x contracts:

- `pyingestkit.cli.app`: Python import remains experimental; the console contract is stable;
- metadata physical SQL layout remains internal although A2 governs logical records/stores;
- provenance low-level helpers remain separate from the A2 `RunManifest` schema promise;
- `replay.materialize_replayed_raw` remains a low-level experimental helper;
- core `Event`/`EventBus`/`EventType`/`HookPolicy` remain experimental;
- `JobRegistry` is promoted because stable B1 plugin helpers return/use it.

B1 promotes logging and plugin discovery helpers to stable candidates; remaining experimental items
are explicitly excluded from the 1.x compatibility promise until separately promoted.

## 17. Internal rule

Everything not listed in the public manifest is `INTERNAL` by default, including underscored
helpers, implementation modules, provider-specific internals and CLI plumbing.

An import such as:

```python
from pyingestkit.runtime._internal import Something
```

would not create a compatibility promise merely because Python can resolve it.

## 18. A1 regression gates

A1 adds machine checks for:

- exact namespace export snapshots;
- exception inventory and replay hierarchy;
- CLI command names;
- Python support classifiers;
- optional extra names;
- reference plugin entry-point group;
- no mandatory boto3/psycopg/openpyxl/PyArrow dependency;
- no core dependency on S3/PostgreSQL implementations;
- no orchestration-platform dependency in core packaging.

This makes public-surface changes deliberate: a contributor must update the manifest and explain the
classification change rather than accidentally changing the API.

## 19. Deferred to later V1 milestones

The A1 deferrals for persistent compatibility and operational surfaces are now resolved by A2 and
B1 respectively. Remaining V1 work is:

- real pilot qualification and documentation completion — V1.0.0-b2;
- final release/upgrade/security E2E and release-candidate packaging — V1.0.0-rc1;
- stable version bump, final qualification and immutable `v1.0.0` release tag.

No new ingestion provider or orchestration platform is introduced by these governance milestones.
