# PyIngestKit V1 — Compatibility Contract

Status: **V1.0.0-a2 — Contract Consolidation + Compatibility**

This document is the human-readable companion to:

- `tests/contract/fixtures/public_api_v1.json` — A1 public-surface inventory;
- `tests/contract/fixtures/compatibility_v1.json` — A2 compatibility contract;
- `scripts/check_public_api.py` — public namespace gate;
- `scripts/check_v1_compatibility.py` — model/enum/extension/persistent-format gate.

A1 answered **what is intentionally public**. A2 answers **which observable contracts must now
remain compatible and how they may evolve**.

## 1. Baseline

A2 starts from the fully qualified A1 merge commit:

```text
6a4f93e3b4beec4b67a846d22f909abebc95524c
```

No V0.6 tag or release is moved or republished by this milestone.

## 2. Compatibility dimensions

PyIngestKit treats compatibility as more than importability. The V1 contract covers these
dimensions where explicitly listed in the machine-readable fixture:

```text
namespace exports
model field names/order/default semantics
enum names and serialized values
abstract extension-point method sets
persistent JSON key sets and schema versions
logical metadata record shapes
```

A change can therefore be breaking even when Python still imports successfully.

## 3. Public namespace rule

`tests/contract/fixtures/public_api_v1.json` remains the canonical public namespace inventory.
`scripts/check_public_api.py` now reads that manifest directly instead of carrying a second
hard-coded export list.

This removes a source-of-truth split that existed in V0.6.

Everything outside the governed public inventory remains internal by default.

## 4. Model evolution rule

For dataclass-style public contracts listed in `compatibility_v1.json`:

- existing field names are compatibility-sensitive;
- field order is compatibility-sensitive because positional construction exists in parts of the
  historical API;
- removing or renaming an existing field is breaking;
- changing a field from optional/defaulted to required is breaking;
- an additive field must be optional or have a backward-compatible default;
- semantic changes to an existing field require an explicit compatibility review even if the type
  annotation is unchanged.

The A2 gate snapshots the current field order so accidental constructor drift fails CI.

## 5. Enum evolution rule

Existing enum member names and serialized values are compatibility data.

For example:

```text
LoadMode.APPEND         -> "append"
RunStatus.SUCCESS       -> "SUCCESS"
DiffKind.CHANGED        -> "CHANGED"
ValidationSeverity.ERROR -> "ERROR"
```

Renaming a member or changing its value is breaking. Adding a member is governed rather than
assumed harmless because callers may perform exhaustive matching.

## 6. Extension-point rule

The abstract method sets of these extension boundaries are frozen by A2:

- `Source`;
- `Parser`;
- `Target`;
- `ArtifactStore`;
- `DatasetVersionStore`;
- `MetadataStore`;
- metadata capability ABCs.

The compatibility preference is:

```text
new concrete method with conservative default
    > optional capability ABC
    > new abstract method on an existing V1 extension contract
```

The last option is breaking for third-party implementations and must not happen silently in 1.x.

This preserves the compatibility approach already used when V0.6 added URI/materialization
behavior to `ArtifactStore` without forcing older stores to implement new abstract methods.

## 7. RunManifest schema v1

A2 introduces an explicit machine-readable version on the persisted run manifest:

```json
{
  "schema_version": 1,
  "run_id": "...",
  "job_id": "...",
  "job_version": "..."
}
```

The complete key order is snapshotted by the A2 compatibility fixture.

Within schema version `1`:

- existing keys keep their meanings;
- keys are not silently removed or renamed;
- additive keys require an intentional contract update;
- incompatible semantic changes require a schema-version bump and a documented upgrade/read path.

The field is additive relative to V0.6 manifests and establishes an explicit future evolution
mechanism before V1 stable.

## 8. Dataset persistence formats

A2 formally adopts the versions already present in the V0.4–V0.6 implementation:

| Format | Version field | Current version |
| --- | --- | --- |
| Dataset snapshot | `snapshot_version` | `"1"` |
| Dataset version metadata | `version_schema` | `"1"` |
| Published dataset pointer | `published_schema` | `"1"` |
| Run manifest | `schema_version` | `1` |

The compatibility gate creates an actual filesystem DatasetVersion, reads `version.json`, publishes
it, reads `current.json`, and validates the schema marker plus ordered key set. This tests the real
serializer rather than a duplicated sample payload.

`SnapshotCodec` remains responsible for version-aware decoding and already rejects unsupported
snapshot versions.

## 9. Other machine-readable payloads

A2 snapshots the current key contracts for:

- `DatasetFingerprint.as_dict()`;
- `DatasetDiff.as_dict()`;
- `ReplayContext.as_manifest_dict()`;
- `ValidationIssue.as_dict()`;
- `ValidationReport.as_dict()`.

These formats do not all carry dedicated schema markers today. A2 therefore freezes their current
observable key sets and requires deliberate review for incompatible change. A later schema marker
may be added additively if independent long-lived interchange requires one.

## 10. Metadata compatibility boundary

A2 makes a deliberate distinction between **logical metadata contracts** and **physical database
layout**.

### Governed logical contract

The field names/order of the exported record dataclasses are snapshotted, including:

```text
RunRecord
StepRecord
ArtifactRecord
EventRecord
ValidationRecord
PublicationRecord
TargetLoadRecord
DiffRecord
DatasetVersionRecord
DatasetVersionRunRecord
PublishedDatasetRecord
ReplayRecord
ReproducibilityRecord
```

The method sets of `MetadataStore` and optional capability ABCs are also protected.

### Internal physical layout

SQLAlchemy table definitions, index names, column implementation details and migration mechanics are
**not** the public V1 API.

This is intentional. A future internal migration may change physical storage while preserving the
logical records returned to users and the behavior of the public store/capability interfaces.

Therefore PyIngestKit does not promise that users may bind application logic directly to internal
SQL table layouts.

## 11. Backward-compatible change classes

Generally compatible when governed and tested:

- additive concrete helper methods;
- additive optional/defaulted model fields after fixture update;
- new internal implementations;
- internal physical metadata migrations preserving the logical record API;
- new optional provider adapters behind explicit extras;
- additive JSON fields whose readers are documented to tolerate unknown keys.

Potentially breaking and requiring an explicit V1 decision:

- removal/rename of a stable-candidate export;
- removal/reorder/requiredness change of a governed model field;
- enum value mutation;
- a new abstract method on an existing extension contract;
- removal/rename/semantic rewrite of a persisted key;
- reading old persisted data only with a newly incompatible decoder;
- changing the meaning of an existing replay/version/fingerprint identifier.

## 12. Deprecation path

Before V1 stable, incompatible candidate changes may still be made if they are documented and the
contract snapshots are intentionally updated.

After V1 stable, a public 1.x removal should normally follow:

```text
introduce replacement
  -> retain compatibility alias/path
  -> emit/document deprecation
  -> keep for the documented deprecation window
  -> remove only in the next allowed breaking release
```

Exact warning classes and user-facing deprecation UX are finalized with error/CLI/config stability
in V1.0.0-b1.

## 13. CI and release qualification

`make check` now includes a dedicated `compatibility` target:

```text
scripts/check_public_api.py
scripts/check_v1_compatibility.py
```

The second gate verifies:

- governed enum values;
- governed dataclass field order;
- abstract extension-point method sets;
- RunManifest schema v1;
- Dataset snapshot schema v1;
- DatasetVersion metadata schema v1;
- PublishedDataset pointer schema v1;
- fingerprint/diff/replay/validation machine payload keys.

Because `make release-check` depends on `make check`, compatibility drift is a release-blocking
failure rather than a documentation-only warning.

## 14. Deferred to V1.0.0-b1

A2 does not prematurely freeze the surfaces that the roadmap assigns to b1:

- exact plugin discovery/helper semantics;
- complete configuration/deprecation behavior;
- canonical error import ergonomics;
- exact CLI option/exit-code/human-output stability;
- observability/logging public contract.

A2 protects their already-governed A1 inventory where applicable but does not convert unfinished
product semantics into accidental 1.x promises.

## 15. A2 completion criterion

A2 is qualified when:

```text
public API manifest gate             GREEN
compatibility structural gate        GREEN
persistent format compatibility      GREEN
Python 3.11 / 3.12 / 3.13           GREEN
PostgreSQL E2E                       GREEN
S3 E2E                               GREEN
Object Storage E2E                   GREEN
foundation / release-check           GREEN
Security                             GREEN
post-merge main qualification        GREEN
```

Only after that qualification is V1.0.0-a2 considered sealed.
