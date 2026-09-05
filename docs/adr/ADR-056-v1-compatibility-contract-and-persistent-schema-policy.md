# ADR-056 — V1 compatibility is enforced at logical contracts and versioned persistence boundaries

Status: Accepted for **V1.0.0-a2 — Contract Consolidation + Compatibility**.

## Context

ADR-055 established an explicit inventory of intentionally public PyIngestKit surfaces. That is
necessary but insufficient for V1 stability: an import can remain available while constructor
fields, enum values, extension methods or persisted JSON shapes change incompatibly.

PyIngestKit also persists several long-lived artifacts:

- run manifests;
- Dataset snapshots;
- DatasetVersion metadata;
- publication pointers;
- diff/replay/validation machine payloads;
- queryable metadata records.

A V1 compatibility contract must distinguish user-visible logical data from internal storage
implementation details.

## Decision

### 1. Add a machine-readable compatibility manifest

`tests/contract/fixtures/compatibility_v1.json` is the A2 source of truth for compatibility-sensitive
model fields, enum values, abstract extension-point method sets and persistent machine formats.

It complements rather than replaces the A1 public API inventory.

### 2. Make compatibility an explicit release gate

`make check` gains a dedicated compatibility stage that executes:

```text
scripts/check_public_api.py
scripts/check_v1_compatibility.py
```

The public API checker reads the A1 manifest directly; the prior duplicated hard-coded V0.6 export
set is removed.

### 3. Version RunManifest before V1 stable

Persisted run manifests carry:

```json
"schema_version": 1
```

Existing V0.6 fields retain their meaning. The new field is additive and establishes an explicit
upgrade mechanism before the V1 compatibility promise becomes final.

### 4. Adopt existing Dataset persistence schema markers

A2 recognizes the already-implemented schema versions as compatibility boundaries:

```text
SnapshotCodec.SNAPSHOT_VERSION       = "1"
version.json / version_schema        = "1"
current.json / published_schema      = "1"
RunManifest / schema_version         = 1
```

Incompatible changes require a version bump and a deliberate read/upgrade strategy.

### 5. Freeze abstract extension method sets

The existing abstract method sets of `Source`, `Parser`, `Target`, `ArtifactStore`,
`DatasetVersionStore`, `MetadataStore` and metadata capability ABCs are compatibility-sensitive.

New functionality should prefer an additive concrete default or a separate optional capability to
adding a new abstract method that breaks third-party implementations.

### 6. Freeze existing enum name/value pairs

Existing serialized enum values are part of the compatibility contract. Additions are governed;
renames/value mutations are breaking.

### 7. Treat logical metadata records as public contracts, physical SQL layout as internal

Exported metadata record dataclasses and store/capability behavior are compatibility-sensitive.
SQLAlchemy table definitions, internal index names and physical migration mechanics are not public
contracts.

This permits internal database evolution while preserving the values and behavior returned through
public PyIngestKit interfaces.

## Consequences

Positive:

- compatibility drift becomes machine-detectable in CI;
- public API inventory has one source of truth;
- persistent formats have an explicit evolution policy;
- third-party extension implementations are protected from accidental new abstract methods;
- internal SQL migrations remain possible without promising table-level API stability;
- V1 release qualification now tests real DatasetVersion and publication payloads rather than only
  documentation fixtures.

Costs:

- intentional contract changes require fixture/documentation updates;
- additive model/enum changes receive explicit review rather than being merged invisibly;
- persisted schema evolution now carries an upgrade responsibility when incompatible.

## Alternatives rejected

### Freeze only `__all__`

Rejected because it does not detect model, enum, ABC or persistence incompatibility.

### Treat the SQLAlchemy schema as the public contract

Rejected because it would couple users to one persistence implementation and obstruct internal
migration work.

### Add schema markers to every payload immediately

Rejected as unnecessary churn. A2 explicitly versions the central run manifest and governs existing
versioned Dataset persistence formats. Other payloads are key-snapshotted and may gain additive
schema markers later when independent long-lived interchange justifies them.

### Add new abstract methods as features evolve

Rejected for existing V1 extension contracts. Optional capability interfaces or conservative
concrete defaults provide a safer source-compatibility path.

## Follow-up

V1.0.0-b1 finalizes plugin, configuration, error, CLI and observability stability without weakening
this A2 compatibility gate.
