# ADR-055 — V1 public API and product scope are governed by an explicit manifest

Status: Accepted for V1.0.0-a1.

## Context

PyIngestKit V0.1 through V0.6 accumulated a real public surface through top-level exports,
sub-package `__all__` declarations, CLI commands, plugin entry points, configuration models,
exceptions and persisted runtime concepts.

V0.x could still amend those contracts. V1.0 cannot responsibly promise compatibility unless the
project first distinguishes intentionally public contracts from merely importable implementation
details and freezes the product boundary itself.

Relying only on `pyingestkit.__all__` is insufficient because users also consume explicit public
sub-packages such as `pyingestkit.targets`, `pyingestkit.sources.http`, `pyingestkit.parsers` and
`pyingestkit.artifacts`.

## Decision

V1 uses five public-surface classifications:

```text
PUBLIC_STABLE_CANDIDATE
PUBLIC_EXPERIMENTAL
INTERNAL
DEPRECATED
REMOVE_BEFORE_V1
```

A machine-readable snapshot is stored at:

```text
tests/contract/fixtures/public_api_v1.json
```

Its human-readable reference is:

```text
docs/reference/public-api.md
```

The manifest inventories explicit public namespaces, their exact exported symbols, controlled
exceptions, CLI command names, the plugin entry-point group, configuration-resolution surface,
Python support and optional extras.

The top-level `pyingestkit` export set inherited from V0.6 is a stable candidate. Explicit
sub-package exports are classified independently rather than assuming that all source modules are
public.

Everything not listed by the manifest is internal by default. Python importability alone does not
create a compatibility promise.

The V1 product boundary is separately frozen in:

```text
docs/architecture/product-scope-v1.md
```

It retains reliable batch ingestion, optional PostgreSQL and S3-compatible integrations, replay,
plugins, CLI/configuration and observability while explicitly excluding scheduling/orchestration
platforms, distributed worker infrastructure, catalog/IAM/GUI/SaaS/AI/stream-processing scope.

## Compatibility staging

A1 classifies and snapshots the surface; it does not pretend that every V1 contract is already
final.

```text
A1  public API + scope inventory
A2  backward compatibility + persistent schemas
B1  plugin/config/error/CLI/observability stability
B2  real pilots + documentation
RC1 full stability qualification
```

`PUBLIC_EXPERIMENTAL` therefore means "intentional current surface requiring an explicit decision
before final 1.0", not "free to change silently". Any change must update the manifest and explain
the rationale.

## Consequences

- New public exports become reviewable rather than accidental.
- Removal or rename of an inventoried export fails contract tests unless the snapshot is explicitly
  changed.
- Internal implementation modules can evolve without implying that every import path is stable.
- Metadata records, provenance schema, plugin helpers and logging/CLI Python internals can remain
  experimental until their dedicated V1 milestones.
- The stable 1.x promise can be made incrementally and deliberately instead of retroactively
  treating the whole source tree as public.
- Product-scope expansion requires an explicit architecture decision rather than feature creep.

## Rejected alternatives

### Treat all importable symbols as public

Rejected because Python package internals are naturally importable and this would freeze accidental
implementation details.

### Treat only top-level `pyingestkit.__all__` as public

Rejected because existing documented extension points intentionally live in public sub-packages.

### Freeze every current sub-package export as already stable

Rejected because metadata/persistence, plugin/config/error/CLI and observability contracts have
dedicated V1 consolidation milestones.

### Delay the inventory until RC1

Rejected because later compatibility work needs an explicit A1 baseline to compare against.
