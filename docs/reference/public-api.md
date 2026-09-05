# PyIngestKit V1 — Public API Reference and A1 Classification

Status: **V1.0.0-a1 — Public API Audit + Scope Freeze**

This document is the human-readable companion to the machine-readable snapshot at
`tests/contract/fixtures/public_api_v1.json`.

The A1 question is deliberately narrow:

> Which PyIngestKit surfaces are intentionally public, and which of them are candidates for a
> compatibility promise across the future 1.x line?

A1 is not the final 1.0 compatibility policy. Persistent-schema compatibility is consolidated in
V1.0.0-a2, while plugin/config/error/CLI/observability stability is finalized in V1.0.0-b1.

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
| `pyingestkit.config` | stable candidate surface | exact config stability finalized in b1 |
| `pyingestkit.contracts` | stable candidate | dataset/field contracts |
| `pyingestkit.core` | mixed | execution types stable candidate; events/registry remain experimental |
| `pyingestkit.declarative` | stable candidate | decorators and compiled definitions |
| `pyingestkit.diff` | stable candidate | deterministic dataset diff contract |
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
| `pyingestkit.logging` | experimental | observability contract finalized in b1 |
| `pyingestkit.metadata` | experimental/mixed | stores/capabilities are candidates; records wait for a2 schema review |
| `pyingestkit.plugins` | experimental | extension contract finalized in b1 |
| `pyingestkit.provenance` | experimental | `RunManifest` is a persistent-format concern for a2 |
| `pyingestkit.cli` | experimental Python API | console entry point is public; Typer `app` object is not yet a 1.x promise |

For all namespaces above, the exact current `__all__` set is captured in the JSON snapshot and
checked by `tests/contract/test_public_api_v1.py`.

## 6. Exceptions

The controlled framework hierarchy currently lives in `pyingestkit.core.exceptions` and includes
`IngestionError` plus configuration, discovery, fetch, parse, normalization, validation,
publication, storage, plugin, hook, diff, snapshot, version-store and replay errors.

These exception identities are classified `PUBLIC_STABLE_CANDIDATE` because callers already need
stable classes to catch predictable framework failures and V0.6 contract tests already protect
part of the hierarchy.

The import path is not ideal. V1.0.0-b1 may add a shorter canonical `pyingestkit.errors` namespace,
but it must preserve existing exception identity or a documented compatibility alias rather than
silently breaking callers.

Provider exceptions such as raw SQLAlchemy, psycopg or boto3 errors are not the intended user
contract when PyIngestKit can translate them into a framework-level error.

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

The command names are snapshotted in A1. Exact option names, exit-code semantics, Rich human output
and machine-readable JSON payload stability are inventoried now but finalized in V1.0.0-b1, as
required by the V1 roadmap.

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

A1 inventories these environment-facing names:

```text
PYINGEST_CONFIG
PYINGEST_ENV
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

Configuration is user-facing, but its final 1.x compatibility/deprecation rules are completed in
V1.0.0-b1.

## 12. Plugin inventory

The stable-candidate entry-point group is:

```text
pyingestkit.jobs
```

The current reference package proves external discovery using installable entry points. Job entry
points resolve to framework `Job`/`JobDefinition` compatible objects. Discovery diagnostics and
helper functions remain `PUBLIC_EXPERIMENTAL` until V1.0.0-b1 freezes the external plugin contract.

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

The audit identified several intentionally importable surfaces that should not be silently treated
as already-frozen 1.x contracts:

- `pyingestkit.cli.app`: useful for tests/integration, but console behavior is the product contract;
- metadata record classes: persistence-schema review belongs to a2;
- logging helpers: observability contract belongs to b1;
- plugin discovery helpers/diagnostics: plugin contract belongs to b1;
- provenance/`RunManifest`: persistent schema belongs to a2;
- `replay.materialize_replayed_raw`: low-level helper, not required for ordinary job authoring;
- core events/registry helpers: public today, but extension semantics need b1 review.

They are documented as `PUBLIC_EXPERIMENTAL`, not removed behind users' backs.

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

A1 intentionally does **not** solve:

- persistent schema compatibility/migrations — V1.0.0-a2;
- final backward-compatibility and deprecation mechanics — V1.0.0-a2;
- plugin/config/error/CLI/observability stability — V1.0.0-b1;
- real pilot qualification and documentation completion — V1.0.0-b2;
- final release/upgrade/security E2E — V1.0.0-rc1.

No new ingestion provider or major product capability is introduced by A1.
