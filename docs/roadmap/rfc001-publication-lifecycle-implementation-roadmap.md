# PyIngestKit 2.1.0 — Publication & Lifecycle Governance Implementation Roadmap

## Status

**Accepted implementation roadmap derived from accepted RFC-001.**

**Accepted:** 2026-10-03

Architecture source:

- [RFC-001 — Publication & Lifecycle Governance](../rfc/RFC-001-publication-lifecycle-governance.md)
- [RFC-001 formal architecture review](../rfc/reviews/RFC-001-architecture-review.md)

Stable compatibility baseline:

```text
PyIngestKit 2.0.0
tag    v2.0.0
commit 449ec4c7a92b7a946d63e167e20f3dab1bd5d21c
```

Roadmap derivation baseline:

```text
main
63a5e7d59abe0ca90a4d95c562e9543389e4e0c5
RFC-001 = ACCEPTED
```

This roadmap assigns the first post-2.0 implementation sequence. It does not
change the 2.0 compatibility contract.

---

## 1. Release-line decision

RFC-001 introduces additive capabilities while preserving all frozen 2.0
contracts.

The implementation target is therefore:

```text
PyIngestKit 2.1.0
```

rather than a 2.0.x maintenance release or a new major version.

### Why 2.1.0

The feature line:

- adds qualified governance APIs;
- adds new optional provider capabilities;
- adds lifecycle persistence;
- adds retention/GC and rollback;
- does not remove or reshape 2.0 public contracts;
- does not widen the 11-symbol package root;
- does not change existing version-1 wire-contract semantics.

The 2.0.x line remains reserved for compatible maintenance/security/provider
fixes.

---

## 2. Compatibility baseline that every lot must preserve

Every implementation lot MUST keep these 2.0 contracts unchanged:

```text
pyingestkit.__all__              exact 11-symbol root
IngestionRuntime.run(...)        frozen signature
DatasetPublisher                 frozen Protocol
DatasetVersionStore              frozen Protocol
PublishedDataset                 frozen root type
existing contract-version 1      unchanged meaning
V1 immutable historical tag      unchanged
```

Governance types remain in explicit qualified namespaces for the entire 2.x
line.

A lot that requires changing one of these contracts is blocked and requires a
new architecture decision rather than an incidental compatibility break.

---

## 3. Product-boundary guardrails

2.1.0 owns dataset publication lifecycle governance.

It still does not own:

- distributed scheduling;
- generic DAG orchestration;
- worker fleets/queues;
- IAM/KMS orchestration;
- bucket lifecycle administration;
- cloud provisioning;
- organization-wide approval workflows;
- catalog/control-plane ownership;
- GUI/SaaS administration;
- generic database migration infrastructure.

The governing rule remains:

```text
external orchestration = WHEN
PyIngestKit            = HOW TO INGEST / GOVERN INGESTED DATASET LIFECYCLE
```

---

## 4. Milestone map

The accepted RFC slices A→G map to LOT-23 through LOT-29.
LOT-30 is a promotion-only stable release lot.

| LOT | Candidate | Purpose |
| --- | --- | --- |
| LOT-23 | 2.1.0a1 | Governance domain values + additive ports |
| LOT-24 | 2.1.0a2 | Durable lifecycle ledger + PostgreSQL |
| LOT-25 | 2.1.0a3 | Filesystem conditional publication / CAS |
| LOT-26 | 2.1.0a4 | S3 conditional publication / endpoint conformance |
| LOT-27 | 2.1.0b1 | Retention, holds and guarded garbage collection |
| LOT-28 | 2.1.0b2 | Governed rollback |
| LOT-29 | 2.1.0rc1 | Cross-provider conformance + crash/recovery qualification |
| LOT-30 | 2.1.0 | Stable promotion and release closure |

Dependency chain:

```text
LOT-23
  ↓
LOT-24
  ↓
LOT-25
  ↓
LOT-26
  ↓
LOT-27
  ↓
LOT-28
  ↓
LOT-29
  ↓
LOT-30
```

Later lots may use earlier capability contracts but must not silently revise
their semantics.

---

# LOT-23 — Governance Domain & Ports

## 5. Candidate

```text
2.1.0a1
```

## 6. Goal

Establish provider-neutral lifecycle governance contracts without performing any
new provider side effects.

This lot is deliberately pure-domain/port heavy.

## 7. Required domain values

The implementation naming review may refine spelling, but the semantics are
fixed.

Candidate values:

```text
PublicationOperationId
PublicationRevision
PublicationSnapshot
PublicationIntent
PublicationLifecycleEvent
PublicationLifecycleEventType
ConditionalPublicationOutcome
RetentionPolicy
VersionHold
GarbageCollectionPlan
GarbageCollectionPlanId
DatasetVersionDeletionResult
DatasetVersionDeletionReconciliationResult
```

### PublicationOperationId

Requirements:

- globally unique enough for cross-process persistence;
- distinct from `IngestionRunId`;
- portable string representation;
- deterministic parse/validation;
- no embedded provider identity.

### PublicationRevision

Requirements:

- opaque at framework boundary;
- equality/comparison token only;
- must not expose provider ETag, inode or SQL transaction ID directly;
- initial/unpublished state is explicit;
- supports ABA-safe revision progression.

### RetentionPolicy

First 2.1 contract:

```text
keep_last: int >= 1
min_age_seconds: int >= 0 | None
```

No policy DSL.

## 8. Additive ports

Candidate qualified contracts:

```text
PublicationLedger
ConditionalDatasetPublisher
DatasetVersionGarbageCollector
```

Conceptual shapes:

```python
class PublicationLedger(Protocol):
    def append(self, event: PublicationLifecycleEvent) -> None: ...
    def get_operation(self, operation_id: PublicationOperationId): ...
    def list_operations(self, dataset_id: str, ...): ...
    def list_unresolved(self, dataset_id: str | None = None): ...

class ConditionalDatasetPublisher(Protocol):
    def inspect(self, dataset_id: str) -> PublicationSnapshot: ...
    def compare_and_publish(...): ...

class DatasetVersionGarbageCollector(Protocol):
    def delete(...): ...
    def reconcile_delete(...): ...
```

Exact signatures are frozen at LOT-23 exit and become the 2.1 feature-line
baseline.

## 9. Namespace rule

New surfaces begin under qualified namespaces such as:

```text
pyingestkit.governance
pyingestkit.governance.publication
pyingestkit.governance.lifecycle
pyingestkit.governance.retention
```

No new top-level `pyingestkit` exports.

The precise module split may be simplified during implementation, but no
governance symbol is promoted to the package root in 2.x.

## 10. LOT-23 acceptance criteria

- exact 2.0 root snapshot unchanged;
- frozen `DatasetPublisher` unchanged;
- frozen `DatasetVersionStore` unchanged;
- new domain values reject malformed IDs/timestamps/metadata;
- operation ID + intent fingerprint semantics are executable;
- same operation ID + different intent fails closed;
- publication revision is provider-neutral;
- retention policy validation is deterministic;
- no SQLAlchemy/boto3 provider import from domain/port modules;
- no deletion side effect exists yet;
- no provider capability is advertised yet;
- Python 3.11–3.14 unit/architecture matrices green;
- Ruff, format, mypy, Bandit and pip-audit green.

## 11. LOT-23 exit evidence

Required documentation:

```text
docs/architecture/v2-lot23-governance-domain-ports.md
```

Required machine evidence:

- public qualified namespace snapshot;
- exact stable-root regression;
- Protocol signature regression;
- domain invariant tests.

---

# LOT-24 — Durable Lifecycle Ledger + PostgreSQL

## 12. Candidate

```text
2.1.0a2
```

## 13. Goal

Persist append-only lifecycle intent/outcome evidence durably and recover
unresolved operations after process restart.

## 14. Required adapters

### MemoryPublicationLedger

Purpose:

- unit tests;
- conformance reference;
- deterministic failure injection.

It is not production durability evidence.

### PostgresPublicationLedger

Purpose:

- first durable production ledger;
- multi-process lifecycle evidence;
- restart recovery.

The historical V1 `MetadataStore` contract is not expanded to absorb V2
governance.

## 15. Durable logical records

At minimum:

```text
publication_operation
publication_event
version_hold
```

A future physical schema may use normalized tables or bounded JSON columns, but
the portable domain contract remains independent of SQLAlchemy.

### publication_operation

Must preserve:

- operation ID;
- dataset ID;
- requested version identity;
- ingestion run ID where applicable;
- correlation ID;
- request time;
- intent fingerprint;
- terminal/unresolved state.

### publication_event

Must be append-only and preserve:

- event ID;
- operation ID;
- event type;
- occurred_at;
- portable payload schema version;
- safe provider operation reference where applicable;
- shared failure/uncertainty evidence where applicable.

## 16. Transaction rule

Ledger writes use caller-safe transaction boundaries.

No hidden commit may make a partial multi-record lifecycle transition appear
complete.

For operations that require operation creation + first event atomically:

```text
commit
  -> operation + event visible

rollback
  -> neither visible
```

## 17. Recovery rule

After process restart:

```text
list_unresolved()
  -> durable unresolved operations
  -> enough intent evidence to reconcile
  -> no secret/provider client reconstruction from persisted payload
```

## 18. LOT-24 acceptance criteria

- Memory and PostgreSQL ledgers pass the same behavioral conformance suite;
- PostgreSQL 16 E2E is mandatory;
- duplicate operation ID + same intent is idempotent;
- duplicate operation ID + different intent fails closed;
- lifecycle events are append-only;
- malformed/redacted metadata fails closed;
- credentials/DSNs/tokens never persist in event payloads;
- transaction rollback proves atomic operation/event persistence;
- restart test proves unresolved operation recovery;
- concurrent append ordering has deterministic observable semantics;
- no existing V1 metadata schema/public contract is changed;
- base installation remains PostgreSQL-provider neutral;
- clean wheel without `[postgres]` imports governance domain successfully.

## 19. LOT-24 exit evidence

Required architecture document:

```text
docs/architecture/v2-lot24-lifecycle-ledger-postgres.md
```

Required E2E:

```text
PostgreSQL lifecycle ledger:
create intent
  -> append outcome
  -> restart process
  -> reload operation
  -> query immutable event history
```

---

# LOT-25 — Filesystem Conditional Publication

## 20. Candidate

```text
2.1.0a3
```

## 21. Goal

Implement provider-correct compare-and-swap publication for the local
filesystem profile.

## 22. Correctness model

The portable guarantee is:

```text
same expected revision
  + concurrent writers
  -> exactly one commit
  -> all others CONFLICT
```

A filesystem adapter may use an inter-process lock internally.

The public API does not expose the lock technology.

## 23. Publication revision

The governed pointer must carry enough framework-owned revision evidence to
prevent ABA.

A revision changes on every governed publication, even when the target
DatasetVersion matches an older/currently repeated content version.

Example:

```text
R10 / V1
  ↓ publish V2
R11 / V2
  ↓ rollback V1
R12 / V1
```

A stale writer holding R10 cannot mistake R12 for R10.

## 24. Compatibility with existing 2.0 pointer readers

A governed filesystem pointer must remain readable through the existing 2.0
`get_published(...)` behavior.

Additional governance fields may be additive only.

The existing stable `PublishedDataset` value is not changed.

## 25. Governance opt-in fence

CAS guarantees require all writers for a governed dataset to use the governance
path.

The implementation must make this deployment condition explicit.

It must not claim that a 2.1 governed publisher can prevent an unrelated legacy
2.0 process from blindly replacing the same pointer.

The migration/enablement path must therefore document:

```text
quiesce legacy writers
  -> inspect/bootstrap current pointer revision
  -> enable governed publication
  -> use governance path for subsequent writers
```

## 26. Failure semantics

- stale revision -> CONFLICT;
- lock acquisition failure before side effect -> controlled failure;
- ambiguous failure after possible replace -> UNKNOWN_OUTCOME;
- UNKNOWN_OUTCOME -> reconciliation before retry;
- same operation ID -> idempotent resume/reconcile.

## 27. LOT-25 acceptance criteria

- two OS processes racing from one revision yield exactly one winner;
- loser receives conflict, not success;
- initial publication race yields one winner;
- ABA scenario is rejected;
- pointer replacement remains atomic;
- crash before replace leaves prior pointer readable;
- crash after possible replace is reconcilable;
- 2.0 `get_published(...)` reads governed pointer successfully;
- existing `DatasetPublisher.publish(...)` contract is unchanged;
- legacy-writer coexistence limitation is documented and tested where possible;
- filesystem provider conformance suite is green.

---

# LOT-26 — S3 Conditional Publication

## 28. Candidate

```text
2.1.0a4
```

## 29. Goal

Provide cross-host CAS publication on S3 endpoints that prove the required
conditional-write profile.

## 30. Minimum capability profile

An endpoint may advertise governed conditional publication only when conformance
proves:

1. current pointer inspection returns a conditional revision token;
2. first creation supports atomic create-if-absent;
3. replacement supports atomic compare-and-replace;
4. stale condition failure is distinguishable from provider/internal failure;
5. two hosts racing on one revision yield exactly one winner;
6. provider truth can reconcile acknowledgement loss.

For AWS S3 this maps to conditional `PutObject` semantics using:

```text
If-None-Match: *
If-Match: <ETag>
```

Provider ETags remain internal adapter tokens and never become
`PublicationRevision` values directly.

## 31. Capability advertisement

Ordinary S3 `put_replace` support is insufficient.

If an endpoint cannot prove the required semantics:

```text
DatasetPublisher                  may remain supported
ConditionalDatasetPublisher       MUST NOT be advertised
```

No optimistic emulation.

## 32. S3 client boundary

The minimal S3 client Protocol may be extended internally/additively to express
conditional object write/delete operations.

boto3 remains lazily imported behind the `[s3]` extra.

## 33. LOT-26 acceptance criteria

- cross-host conditional publication test;
- exactly-one-winner concurrent race;
- initial create race;
- stale ETag/token maps to framework conflict;
- provider error maps to controlled failure;
- acknowledgement-loss simulation produces UNKNOWN_OUTCOME;
- reconciliation observes provider truth without republishing;
- provider token never leaks into portable public revision contract;
- unsupported endpoint profile fails capability qualification;
- existing S3 artifact/version storage and replay tests remain green;
- no mandatory boto3 dependency in base install.

## 34. Release blocker rule

LOT-26 cannot be closed on a mocked structural Protocol alone.

At least one CI S3 endpoint profile must prove the required conditional
semantics end-to-end.

If the current CI S3-compatible service does not support them, the milestone
remains open until a qualifying profile is available.

---

# LOT-27 — Retention, Holds & Guarded Garbage Collection

## 35. Candidate

```text
2.1.0b1
```

## 36. Goal

Introduce deterministic retention planning and explicit destructive lifecycle
execution without compromising immutable history safety.

## 37. Holds

Required lifecycle events:

```text
HOLD_PLACED
HOLD_RELEASED
```

A held version is never GC-eligible.

A hold is framework lifecycle evidence, not a provider object lock.

## 38. Retention planner

Input:

```text
DatasetVersion inventory
+ current publication snapshot
+ active holds
+ unresolved lifecycle operations
+ RetentionPolicy
```

Output:

```text
GarbageCollectionPlan
```

Planning is pure and performs no deletion.

## 39. Mandatory protections

A version is protected when:

- it is current;
- it is held;
- an unresolved publication references it;
- an unresolved rollback references it;
- its identity/integrity cannot be verified;
- the plan evidence is stale.

These protections are not policy switches.

## 40. Plan fingerprint

Each plan carries a deterministic evidence fingerprint over the lifecycle state
used to produce it.

Execution must detect stale evidence before destructive action.

## 41. Garbage collectors

First provider targets:

```text
FileDatasetVersionGarbageCollector
S3DatasetVersionGarbageCollector
```

Deletion capability remains separate from frozen `DatasetVersionStore`.

## 42. Delete uncertainty

Deletion-specific result values reuse:

- `FailureEvidence`;
- `Retryability`;
- `OutcomeUncertainty`.

They do not reuse publication result classes.

## 43. LOT-27 acceptance criteria

- `keep_last` deterministic selection;
- `min_age_seconds` deterministic selection using aware timestamps;
- current version never selected;
- held version never selected;
- unresolved-operation version never selected;
- plan fingerprint changes when protected lifecycle state changes;
- stale plan cannot delete newly protected/current version;
- filesystem delete binds to canonical in-root reference;
- filesystem symlink/path escape is rejected;
- S3 delete binds to canonical bucket/prefix key;
- arbitrary caller-supplied destructive path/key is rejected;
- delete success emits durable evidence;
- delete failure emits durable controlled evidence;
- uncertain delete requires reconciliation;
- repeat execution of completed plan is safe;
- File/S3 GC semantics pass common conformance.

---

# LOT-28 — Governed Rollback

## 44. Candidate

```text
2.1.0b2
```

## 45. Goal

Make rollback an explicit governed publication of an already-existing immutable
DatasetVersion.

## 46. Rollback invariants

```text
rollback != version mutation
rollback != history deletion
rollback != replay
rollback = new publication operation to historical immutable version
```

Every successful rollback advances the publication revision.

## 47. Required behavior

A rollback request must specify:

- dataset;
- target historical version;
- expected publication revision;
- operation identity;
- correlation/run evidence as applicable.

The target must already exist and pass DatasetVersion integrity verification.

## 48. Concurrency

Example:

```text
actor A observes R20/V5
actor B publishes V6 -> R21
actor A requests rollback to V3 with expected R20
        ↓
CONFLICT
```

Rollback never silently overrides a newer publication.

## 49. Outcome uncertainty

A rollback with ambiguous provider acknowledgement follows the exact same
reconciliation requirement as ordinary governed publication.

No blind retry.

## 50. Replay boundary

Replay remains `publish=False` by default.

A future explicit replay publication may compose with governed publication, but
LOT-28 does not make replay automatically publish or rollback.

## 51. LOT-28 acceptance criteria

- rollback target must exist;
- rollback target integrity must verify;
- rollback uses CAS;
- stale revision conflicts;
- successful rollback advances revision;
- rollback to same historical version again is a distinct operation/revision;
- durable ROLLBACK_REQUESTED/COMMITTED evidence exists;
- UNKNOWN_OUTCOME rollback is reconcilable;
- failed rollback never mutates DatasetVersion bytes;
- strict replay behavior remains unchanged.

---

# LOT-29 — Full Governance Conformance & RC

## 52. Candidate

```text
2.1.0rc1
```

## 53. Goal

Prove the complete 2.1 governance contract across built artifacts, processes,
hosts and provider combinations before stable promotion.

No new architecture is introduced in this lot.

## 54. Required conformance matrix

### Domain/ports

- exact qualified namespace exports;
- exact Protocol signatures;
- operation identity/idempotency;
- retention policy;
- failure/uncertainty semantics.

### Ledger

- Memory conformance;
- PostgreSQL conformance;
- restart recovery;
- rollback/atomicity of ledger writes.

### Filesystem publication

- process contention;
- CAS races;
- ABA;
- crash before/after side effect;
- reconciliation.

### S3 publication

- cross-host races;
- create-if-absent;
- compare-and-replace;
- acknowledgement loss;
- unsupported capability profile.

### GC

- File + S3;
- current/held/unresolved protections;
- stale plan;
- deletion uncertainty/reconciliation.

### Rollback

- File + S3 governed publication;
- conflicts;
- durable evidence;
- uncertain acknowledgement.

## 55. Mixed-provider E2E

At minimum, prove:

```text
PostgreSQL PublicationLedger
        +
S3 conditional publication pointer
        +
S3 DatasetVersionStore
        ↓
governed publish
        ↓
process restart
        ↓
ledger reload
        ↓
reconciliation / retention / rollback
```

and:

```text
PostgreSQL PublicationLedger
        +
filesystem conditional publisher
        +
filesystem DatasetVersionStore
        ↓
same observable governance semantics
```

## 56. Fault-injection matrix

Fault injection must cover:

- crash after durable intent before provider side effect;
- crash after provider commit before ledger outcome append;
- acknowledgement loss;
- stale revision;
- lock acquisition failure;
- stale GC plan;
- delete acknowledgement loss;
- process restart with unresolved operation.

Fault tests must never report synthetic provider success without observable
provider truth.

## 57. Built-artifact qualification

The RC must prove governance from the built wheel/source distribution, not only
from editable checkout.

Required:

- clean wheel base install;
- clean wheel + postgres extra;
- clean wheel + s3 extra;
- optional provider isolation;
- no accidental top-level exports;
- exact 2.0 stable-root regression.

## 58. Security qualification

Required negatives:

- lifecycle event secret redaction;
- credential-bearing locator rejection;
- DSN password redaction;
- filesystem path escape;
- symlink escape;
- foreign S3 bucket/prefix deletion attempt;
- malformed revision/token;
- intent-ID collision with changed intent;
- destructive operation with stale evidence.

## 59. LOT-29 acceptance criteria

All prior lot criteria must pass on one final RC head.

Release-blocking CI adds explicit jobs for:

```text
governance-contract
governance-postgres-e2e
governance-filesystem-cas
governance-s3-cas
governance-gc-e2e
governance-rollback-e2e
governance-cross-provider-e2e
governance-built-artifact
governance-security-negatives
```

The existing 2.0 release gates remain mandatory.

---

# LOT-30 — PyIngestKit 2.1.0 Stable Promotion

## 60. Candidate

```text
2.1.0
```

## 61. Goal

Promote the unchanged qualified 2.1.0rc1 governance contract to stable.

LOT-30 is promotion-only.

No new governance capability or signature change is allowed.

## 62. Stable freeze

The stable 2.1 feature contract records at minimum:

- qualified governance namespace exports;
- exact new Protocol signatures;
- retention policy schema;
- lifecycle event schema versions;
- operation/revision serialization;
- provider compatibility matrix;
- GC/rollback result contracts.

The original 2.0 root/provider/wire baseline remains separately regression
tested.

## 63. Release-blocking matrix

Before stable merge:

- Python 3.11–3.14 tests;
- Python 3.11–3.14 architecture gates;
- all LOT-29 governance gates;
- Ruff/format/mypy;
- Bandit/pip-audit;
- PostgreSQL lifecycle E2E;
- filesystem CAS E2E;
- S3 CAS E2E;
- File/S3 GC;
- governed rollback;
- mixed-provider cross-host E2E;
- clean wheel/sdist;
- optional-provider isolation;
- V1 immutable history;
- exact 2.0 compatibility snapshot;
- strict docs build;
- terminal stable release gate.

After merge, the exact merge SHA must pass CI, Security and Docs before the
`v2.1.0` tag/release is created.

---

## 64. Global definition of done

The 2.1.0 feature line is complete only when all statements below are true.

### Compatibility

- 2.0 root remains exact;
- 2.0 Protocols remain exact;
- 2.0 applications do not need governance APIs;
- new APIs remain qualified namespaces;
- V1 historical evidence remains immutable.

### Publication correctness

- CAS proves exactly-one-winner semantics;
- ABA is prevented;
- UNKNOWN_OUTCOME never triggers blind retry;
- reconciliation observes provider truth;
- operation identity is durable/idempotent.

### Lifecycle durability

- PostgreSQL lifecycle evidence survives restart;
- event history is append-only;
- secrets are not persisted;
- unresolved operations can be recovered.

### GC safety

- current/held/unresolved versions are protected;
- planning is separate from deletion;
- stale plans are blocked;
- destructive locators are canonical/provider-confined;
- uncertain deletes are reconciled.

### Rollback

- historical versions remain immutable;
- rollback is a new publication;
- rollback is CAS-protected;
- history/evidence remains auditable.

### Provider equivalence

- filesystem and S3 publication expose equivalent observable semantics;
- File/S3 GC exposes equivalent observable semantics;
- unsupported S3 conditional capability is fail-closed.

---

## 65. Branching strategy

Recommended implementation branches:

```text
feat/v2.1-governance-foundations        LOT-23
feat/v2.1-lifecycle-ledger              LOT-24
feat/v2.1-filesystem-cas                LOT-25
feat/v2.1-s3-cas                        LOT-26
feat/v2.1-retention-gc                  LOT-27
feat/v2.1-rollback                      LOT-28
release/v2.1.0-rc1                      LOT-29
release/v2.1.0                          LOT-30
```

Each branch begins from the exact merged predecessor milestone.

No parallel branch may assume an unmerged contract from a later lot.

---

## 66. Promotion policy

Every lot requires:

1. implementation complete;
2. exact-head CI green;
3. Security green;
4. Docs green where docs change;
5. lot-specific acceptance evidence;
6. no frozen-contract drift;
7. merge to `main`;
8. post-merge CI verification where the milestone changes release-contract
   evidence.

Version changes occur only when the lot is actually being promoted.

Do not pre-bump later milestone versions on earlier branches.

---

## 67. Stop conditions

Implementation must stop and return to architecture review if any lot discovers
that it requires:

- changing `DatasetPublisher`;
- changing `DatasetVersionStore`;
- changing `PublishedDataset`;
- widening the top-level root;
- weakening UNKNOWN_OUTCOME reconciliation;
- relying on a provider feature that cannot be qualified;
- introducing automatic distributed orchestration;
- making provider infrastructure administration a PyIngestKit responsibility.

A blocked S3 CAS provider profile is not permission to fake or emulate a
correctness guarantee.

---

## 68. Recommended immediate implementation start

Once this roadmap is accepted, implementation begins with:

```text
LOT-23 — 2.1.0a1
Governance Domain & Ports
```

The first code change should establish provider-neutral domain values,
qualified namespace boundaries and exact contract tests before any PostgreSQL,
filesystem or S3 provider behavior is added.
