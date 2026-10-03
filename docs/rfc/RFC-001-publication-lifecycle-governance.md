# RFC-001 — Publication & Lifecycle Governance

**Status:** Accepted  
**Accepted:** 2026-10-03  
**Date:** 2026-10-03  
**Stable compatibility baseline:** PyIngestKit 2.0.0  
**Baseline tag:** `v2.0.0`  
**Qualified stable commit:** `449ec4c7a92b7a946d63e167e20f3dab1bd5d21c`  
**Post-2.0 scope baseline:** `bc5a14e8abde4d057d71ce196dae4aca9ae08887`

> This RFC is an architecture proposal, not a roadmap milestone. It does not
> create LOT-23, does not assign a 2.x release number and does not modify the
> frozen 2.0 contracts.

---

## 1. Context

PyIngestKit 2.0 already provides the core publication foundations:

```text
DatasetVersionStore
        |
        +--> immutable DatasetVersion history
        |
        v
DatasetPublisher
        |
        +--> publish(...)
        +--> get_published(...)
        |
        v
PublishedDataset
        |
        v
current publication pointer
```

LOT-08 established the separation between immutable version persistence and
publication. LOT-15 extended the same model to S3-compatible object storage.
The stable 2.0 publication service also models provider outcome uncertainty and
requires reconciliation before an uncertain publication can be treated as
committed or retried.

The post-2.0 scope review identified five still-open lifecycle concerns:

- durable V2 lifecycle metadata;
- compare-and-swap publication;
- distributed publication coordination;
- retention and garbage collection;
- governed rollback.

These concerns are cohesive because they all answer one production question:

> How can PyIngestKit safely govern a long-lived dataset publication lifecycle
> when several processes, hosts or operators may act on the same immutable
> version history?

---

## 2. Existing 2.0 invariants

This RFC MUST preserve the following stable invariants.

```text
physical write != governed publication
DatasetVersion = immutable
PublishedDataset = explicit current pointer
Replay != live reacquisition
UNKNOWN_OUTCOME = reconciliation required
ArtifactStore != DatasetVersionStore
DatasetVersionStore != target materialization
PyIngestKit != orchestrator
```

A version may exist without being published.

Publishing does not mutate the immutable DatasetVersion.

Replay does not implicitly republish.

Provider side effects with uncertain outcomes are never blindly retried.

---

## 3. Compatibility constraint

The 2.0 `DatasetPublisher` Protocol is frozen:

```python
class DatasetPublisher(Protocol):
    def publish(
        self,
        reference: DatasetVersionReference,
        *,
        ingestion_run_id: IngestionRunId,
        published_at: datetime,
    ) -> PublishedDataset: ...

    def get_published(self, dataset_id: str) -> PublishedDataset | None: ...
```

This RFC therefore MUST NOT add CAS tokens, locks, operation IDs or lifecycle
arguments to those methods.

The existing `PublishedDataset` root type also remains unchanged.

Any future implementation of this RFC must be additive:

```text
2.0 stable contracts
        |
        +--> remain valid and unchanged
        |
        v
new governance contracts
        |
        +--> optional capability ports
        +--> new governance service
        +--> new durable lifecycle evidence
```

Existing 2.0 applications that only use `DatasetPublisher` must continue to
work without adopting lifecycle governance.

---

## 4. Goals

The proposal aims to provide:

1. safe concurrent publication;
2. durable publication intent and outcome evidence;
3. compare-and-swap semantics over the authoritative current pointer;
4. deterministic conflict detection;
5. reconciliation after uncertain provider outcomes;
6. retention planning over immutable version history;
7. guarded garbage collection with durable deletion evidence;
8. explicit rollback to a historical immutable version;
9. provider-equivalent behavior across filesystem, S3-compatible and SQL-backed
   implementations;
10. a provider-neutral model that does not require distributed orchestration.

---

## 5. Non-goals

This RFC does not introduce:

- a scheduler;
- a worker queue;
- a generic workflow/DAG engine;
- automatic source reacquisition;
- bucket lifecycle administration;
- S3 replication configuration;
- IAM/KMS orchestration;
- database schema migration as a general platform capability;
- organization-wide approval workflows;
- a GUI/control plane;
- automatic deletion through cloud-provider lifecycle rules;
- V1 Job/Pipeline/Step compatibility aliases.

Retention and GC are PyIngestKit dataset-lifecycle semantics, not cloud
infrastructure provisioning.

---

## 6. Proposed architecture

The proposal introduces four logical responsibilities around the existing
stable contracts.

```text
                 immutable DatasetVersion
                          |
                          v
                 DatasetVersionStore
                          |
                          v
                Governance Service
             /          |           \
            /           |            \
           v            v             v
 Publication Ledger   CAS Publisher   Retention Planner
           |            |             |
           |            v             v
           |       current pointer   GC Plan
           |                          |
           +--------------------------+
                          |
                          v
                    lifecycle evidence
```

The exact Python names remain subject to implementation-level naming review; the responsibilities and boundaries are accepted.

### 6.1 Publication ledger

A new provider-neutral ledger records append-only lifecycle evidence.

Candidate responsibility:

```text
PublicationLedger
  append(event)
  get_operation(operation_id)
  list_operations(dataset_id, ...)
  list_unresolved(dataset_id)
```

The ledger is NOT the authoritative current publication pointer.

Its purpose is durable intent, outcome, reconciliation and audit evidence.

### 6.2 Conditional publication capability

A new additive capability port provides compare-and-swap publication.

Candidate responsibility:

```text
ConditionalDatasetPublisher
  inspect(dataset_id) -> PublicationSnapshot
  compare_and_publish(
      reference,
      expected_revision,
      operation_id,
      ingestion_run_id,
      published_at,
  ) -> ConditionalPublicationOutcome
```

An adapter may implement both the frozen `DatasetPublisher` and the new
conditional capability.

The old Protocol remains untouched.

### 6.3 Retention planner

Retention selection is pure policy evaluation.

```text
version inventory
    +
published pointer
    +
holds / unresolved operations
    +
retention policy
        |
        v
GarbageCollectionPlan
```

Planning performs no deletion.

### 6.4 Garbage-collection capability

Deletion requires a separate optional port because the stable
`DatasetVersionStore` intentionally has no delete method.

Candidate responsibility:

```text
DatasetVersionGarbageCollector
  delete(reference, expected_evidence) -> DeletionEvidence
```

This prevents lifecycle deletion semantics from being retrofitted onto the
frozen `DatasetVersionStore` Protocol.

---

## 7. Lifecycle evidence model

The durable evidence model should be append-only.

Candidate event families:

```text
VERSION_OBSERVED
PUBLICATION_REQUESTED
PUBLICATION_COMMITTED
PUBLICATION_CONFLICT
PUBLICATION_OUTCOME_UNKNOWN
PUBLICATION_RECONCILED_COMMITTED
PUBLICATION_RECONCILED_NOT_COMMITTED
PUBLICATION_RECONCILED_CONFLICT
ROLLBACK_REQUESTED
ROLLBACK_COMMITTED
RETENTION_PLAN_CREATED
GC_DELETE_REQUESTED
GC_DELETE_COMMITTED
GC_DELETE_FAILED
```

Each event should carry only portable, non-secret evidence such as:

- event identifier;
- schema version;
- dataset identifier;
- optional dataset-version identity;
- optional publication operation identifier;
- ingestion run identifier where applicable;
- correlation identifier;
- timezone-aware occurrence timestamp;
- event type;
- provider operation reference when safe to persist;
- prior/next publication revision where applicable;
- failure category / uncertainty evidence where applicable.

Credentials, bearer tokens, connection strings and provider client objects are
forbidden.

---

## 8. Publication operation identity

Every governed publication attempt requires a stable operation identifier.

The operation identifier provides idempotency across process restarts:

```text
same operation_id + same intent
    -> return/reconcile same semantic operation

same operation_id + different intent
    -> fail closed
```

The identifier is distinct from:

- `IngestionRunId`;
- dataset version ID;
- provider request ID;
- correlation ID.

One ingestion run may produce more than one explicit publication action over
time, and one publication may need reconciliation after the originating process
has terminated.

---

## 9. Compare-and-swap semantics

### 9.1 Why version ID alone is insufficient

A comparison based only on the current version ID is vulnerable to ABA:

```text
A -> B -> A
```

A stale actor that only observed version A cannot distinguish the original A
publication from a later return to A.

The governance layer therefore needs an opaque publication revision.

### 9.2 Publication snapshot

A conditional read returns conceptually:

```text
PublicationSnapshot
  published_dataset: PublishedDataset | None
  revision: opaque PublicationRevision
```

The revision has comparison semantics but no cross-provider physical meaning.

It must not expose an S3 ETag, SQL transaction ID or filesystem inode as a
portable framework contract.

### 9.3 CAS rule

A publication succeeds only when the expected revision still matches provider
truth.

```text
expected revision == current revision
        -> attempt atomic pointer replacement

expected revision != current revision
        -> CONFLICT
        -> no publication side effect
```

Exactly one concurrent writer may win from the same expected revision.

### 9.4 Initial publication

An un-published dataset has an explicit initial revision state. Two concurrent
first publishers using that same initial state must still produce one winner
and one conflict.

---

## 10. Provider implementation semantics

The provider-neutral contract defines observable behavior, not one locking
mechanism.

### 10.1 Filesystem

A filesystem implementation may use an inter-process lock around:

```text
lock
  -> read current revision
  -> compare
  -> replace current.json atomically
  -> release
```

The lock is an adapter mechanism, not a framework-wide public lock API.

### 10.2 S3-compatible object storage

An S3-compatible adapter should use a qualified conditional object-write
mechanism where the endpoint supports it.

The provider token used for the conditional request remains internal.

If the configured S3-compatible endpoint cannot prove atomic conditional
replacement, the CAS capability MUST NOT be advertised merely because ordinary
`put_replace` works.

### 10.3 SQL-backed pointer

A SQL adapter may use a row revision:

```sql
UPDATE publication_state
SET ...
WHERE dataset_id = ?
  AND revision = ?
```

Zero rows updated means conflict.

### 10.4 Distributed locks

Distributed locks are not the primary portable correctness contract.

They may be used internally by an adapter or deployment when a provider lacks a
native conditional primitive, but:

- lock acquisition failure must be explicit;
- lease expiry or lock ownership uncertainty must never be reported as success;
- loss of a lock after a possible side effect may require reconciliation;
- a lock must not replace durable operation evidence.

The portable guarantee is conditional publication, not a particular lock
technology.

---

## 11. Publication state machine

A governed publication follows this conceptual state machine.

```text
REQUESTED
   |
   | durable intent
   v
READY
   |
   | CAS attempt
   +--------------------+
   |                    |
   v                    v
COMMITTED             CONFLICT
   |
   +------------------------------+
   |
provider acknowledgement uncertain
   |
   v
UNKNOWN_OUTCOME
   |
   | reconcile provider truth
   +-------------------+-------------------+
   |                   |                   |
   v                   v                   v
CONFIRMED_COMMITTED  NOT_COMMITTED       CONFLICT
```

No automatic publication retry is permitted from `UNKNOWN_OUTCOME` before
reconciliation.

---

## 12. No distributed transaction requirement

The proposal deliberately does not require XA/two-phase commit across SQL
metadata and object storage.

Instead it uses durable intent plus reconciliation:

```text
1. append PUBLICATION_REQUESTED
2. attempt provider CAS
3. append observed outcome

crash between 2 and 3
    -> operation remains unresolved
    -> reconciliation inspects provider truth
    -> append reconciliation evidence
```

This model remains viable when the pointer lives in S3 and lifecycle evidence
lives in PostgreSQL.

The ledger must never fabricate provider success merely because the intent was
persisted.

---

## 13. Relationship with current outcome uncertainty

The existing 2.0 publication model already defines:

- `PublicationStatusV2.UNKNOWN_OUTCOME`;
- `FailureCategory.UNKNOWN_OUTCOME`;
- `OutcomeUncertainty.REQUIRES_RECONCILIATION`;
- `PublicationServiceV2.reconcile(...)`.

The governance design must extend these semantics rather than create a second
incompatible uncertainty model.

Future implementation may introduce a new governance service while preserving
the existing 2.0 service unchanged for compatibility.

---

## 14. Durable SQL lifecycle metadata

The first durable metadata target should be PostgreSQL, but the logical port
must remain provider-neutral.

A SQL schema is expected to model at least:

```text
publication_operation
  operation_id
  dataset_id
  requested_version_id
  ingestion_run_id
  correlation_id
  requested_at
  terminal_status / unresolved marker

publication_event
  event_id
  operation_id
  event_type
  occurred_at
  payload_schema
  portable evidence

version_lifecycle
  dataset_id
  version_id
  optional hold/pin evidence
  observed_at
```

Physical table names, indexes and SQLAlchemy mappings are adapter internals until
an explicit persistence contract says otherwise.

Lifecycle evidence must remain queryable after the original process exits.

---

## 15. Retention policy semantics

Retention applies only to immutable dataset versions.

A policy may select candidates by portable criteria such as:

- minimum number of newest versions to retain;
- minimum age before eligibility;
- explicit hold/pin;
- publication history requirements.

The first accepted policy model should stay deterministic and explainable.

Provider-specific storage-class transitions are out of scope.

---

## 16. GC safety invariants

A version MUST NOT be deleted when any of these is true:

1. it is the currently published version;
2. it is protected by an explicit hold/pin;
3. it is referenced by an unresolved publication operation;
4. it is referenced by a rollback operation that has not reached a terminal
   state;
5. the GC plan was created against stale publication/lifecycle evidence;
6. integrity or identity checks cannot be completed.

Deletion is fail-closed.

---

## 17. Two-phase garbage collection

Garbage collection is intentionally split into planning and execution.

### Phase A — plan

```text
inventory + policy + lifecycle state
        |
        v
GarbageCollectionPlan
  plan_id
  created_at
  dataset_id
  protected versions
  candidate versions
  evidence fingerprint
```

### Phase B — execute

Before each delete, execution revalidates the relevant current state.

```text
candidate
  -> revalidate
  -> delete physical immutable version
  -> verify absence/provider result
  -> append deletion evidence
```

A stale plan is rejected or partially blocked; it is never blindly executed.

---

## 18. Deletion outcome uncertainty

Object deletion can also be uncertain.

If a provider may have deleted an object but acknowledgement was lost, the
framework must record uncertainty and reconcile with provider truth.

The same rule applies:

```text
UNKNOWN_OUTCOME
    -> inspect
    -> confirm deleted / confirm present / conflict / still unknown
```

Automatic repeated delete is only safe when the provider's delete semantics are
proven idempotent for the exact operation.

---

## 19. Governed rollback

Rollback does not mutate historical DatasetVersion objects and does not erase
publication history.

Rollback means:

> explicitly publish a previously created immutable DatasetVersion as the new
> current version, under the same CAS and lifecycle-evidence rules as any other
> governed publication.

Therefore rollback is both:

- pointer movement; and
- a new durable publication event.

```text
current = V5
rollback target = V3
        |
        v
new publication operation
expected_revision = R12
target = V3
        |
        v
current = V3
revision = R13
history preserved
```

A rollback to the same content-addressed version later is still a distinct
publication operation and must receive a new publication revision.

---

## 20. Replay interaction

Strict replay continues to default to `publish=False`.

This RFC does not make replay publication implicit.

A future explicit replay-publication feature may call the same governed
publication capability only after replay has produced/verified the desired
immutable version.

This preserves:

```text
replay success != publication success
```

---

## 21. Failure taxonomy

At minimum, a future implementation must distinguish:

| Condition | Semantic result |
| --- | --- |
| expected revision stale | conflict |
| lock/capability unavailable before side effect | failed / retryable as explicitly classified |
| provider may have committed | unknown outcome / reconciliation required |
| same operation ID, same intent | idempotent resume/reconcile |
| same operation ID, different intent | fail closed |
| current version selected for GC | protected / rejected |
| GC evidence stale | stale-plan conflict |
| provider may have deleted | unknown deletion outcome |
| integrity mismatch | controlled failure, no publication/GC continuation |

Raw provider exceptions are not the portable public contract.

---

## 22. Security and evidence policy

Lifecycle metadata may contain identifiers and operational references but no
secrets.

The implementation must:

- redact credentials and authorization headers;
- avoid persisting DSNs with passwords;
- avoid serializing SDK clients or sessions;
- validate provider locators before destructive actions;
- bind GC deletion to canonical stored references;
- preserve correlation/run IDs for audit;
- use timezone-aware timestamps;
- fail closed on malformed lifecycle records.

Retention/GC must not accept arbitrary filesystem paths or object keys supplied
directly by an untrusted caller when a canonical DatasetVersionReference exists.

---

## 23. Observability

Human-readable logging should preserve PyIngestKit's established terminal
format and add governance context through existing correlation fields.

Structured evidence should carry full IDs.

Recommended event dimensions include:

```text
dataset_id
version_id
publication_operation_id
publication_revision
ingestion_run_id
correlation_id
gc_plan_id
provider kind
outcome / uncertainty
```

DEBUG-only provider details must remain behind verbose/debug logging.

---

## 24. Provider conformance requirements

A provider claiming governed publication support must pass behavioral
conformance, not merely structural typing.

### Publication

- two writers from the same expected revision -> exactly one commit;
- loser observes conflict, not success;
- same operation ID + same intent is idempotent;
- same operation ID + changed intent fails closed;
- stale expected revision never overwrites newer truth;
- an acknowledged success can be read back;
- uncertain acknowledgement requires reconciliation;
- reconciliation never republishes as a side effect.

### Filesystem

- cross-process contention is qualified;
- atomic pointer replacement remains intact;
- crash/temporary-file behavior is safe.

### S3-compatible

- cross-host contention is qualified;
- conditional object replacement is proven on the supported endpoint profile;
- unsupported conditional semantics are detected rather than emulated
  optimistically.

### SQL

- row-revision CAS is atomic;
- transaction rollback cannot expose partial lifecycle records;
- concurrent updates produce deterministic conflict semantics.

---

## 25. Retention/GC conformance requirements

- current published version is never deleted;
- held/pinned version is never deleted;
- unresolved publication reference blocks deletion;
- stale GC plan cannot delete a newly protected version;
- deletion evidence is durable;
- repeated execution of an already completed plan is safe;
- unknown delete outcome is reconcilable;
- integrity mismatch blocks destructive action;
- File and S3 implementations produce equivalent lifecycle semantics.

---

## 26. Rollback conformance requirements

- rollback target must already exist as an immutable DatasetVersion;
- rollback uses CAS against the caller's observed revision;
- concurrent newer publication causes rollback conflict;
- rollback creates new durable operation evidence;
- rollback never rewrites DatasetVersion bytes;
- rollback to a previously published version still creates a new publication
  revision;
- rollback outcome uncertainty follows the same reconciliation rules as normal
  publication.

---

## 27. Compatibility strategy

If accepted, implementation must preserve all of these 2.0 surfaces unchanged:

- the 11-symbol stable package root;
- `DatasetPublisher`;
- `DatasetVersionStore`;
- `PublishedDataset`;
- `IngestionRuntime.run(...)`;
- existing version-1 portable wire contracts.

New governance APIs should initially live in explicit qualified namespaces and
be promoted only after conformance and release-contract review.

No provider may claim governance support merely because it already satisfies
the 2.0 `DatasetPublisher` Protocol.

---

## 28. Candidate implementation sequence

This is a technical decomposition only, not an approved LOT roadmap.

### Slice A — domain and ports

- operation identity;
- publication revision/snapshot;
- lifecycle event model;
- publication ledger Protocol;
- conditional publication Protocol;
- GC plan/evidence values;
- garbage-collection Protocol.

### Slice B — durable ledger

- provider-neutral repository contract;
- PostgreSQL lifecycle metadata adapter;
- atomic append/query tests;
- unresolved-operation recovery.

### Slice C — conditional filesystem publication

- inter-process coordination;
- revision-aware compare-and-publish;
- crash safety;
- concurrency tests.

### Slice D — conditional S3 publication

- conditional object replacement;
- cross-host races;
- unknown acknowledgement simulation;
- endpoint capability qualification.

### Slice E — retention and GC

- deterministic policy;
- plan fingerprint;
- protected-version rules;
- filesystem and S3 destructive adapters;
- deletion reconciliation.

### Slice F — rollback

- explicit rollback request;
- CAS publication to historical version;
- durable rollback evidence;
- race and reconciliation tests.

### Slice G — full conformance

- File/S3/PostgreSQL semantic matrix;
- clean-wheel/provider-isolation checks;
- crash/restart scenarios;
- cross-host E2E;
- security and redaction checks.

Only after these slices are accepted as roadmap work should they receive LOT
numbers and release versioning.

---

## 29. Acceptance criteria for this RFC

The RFC may move from **Proposed** to **Accepted** only when reviewers agree
that:

- existing frozen 2.0 contracts remain unchanged;
- CAS, not blind overwrite, is the concurrency correctness primitive;
- publication operation identity is durable and idempotent;
- UNKNOWN_OUTCOME requires reconciliation before retry;
- no distributed transaction across SQL/object storage is required;
- rollback is a new governed publication to an existing immutable version;
- retention planning and deletion execution are separate;
- current/held/unresolved versions are protected from GC;
- deletion uncertainty is explicitly modeled;
- provider conformance proves equivalent observable semantics;
- infrastructure administration remains out of scope.

Acceptance authorizes implementation planning, not implementation itself.

---

## 30. Resolved review decisions

The six architecture-review questions are resolved by the formal
[RFC-001 architecture review](reviews/RFC-001-architecture-review.md):

1. **Lifecycle ledger:** provider-neutral Protocol + in-memory reference adapter
   + PostgreSQL as the first durable production implementation. A second durable
   local backend is deferred.
2. **S3 CAS profile:** advertise conditional publication only when endpoint
   conformance proves atomic create-if-absent and compare-and-replace semantics,
   corresponding to `If-None-Match` / `If-Match` for AWS S3.
3. **Holds/pins:** included in the first retention/GC slice and mandatory for
   GC protection.
4. **Retention policy:** first stable schema is limited to `keep_last` and
   optional `min_age_seconds`; current/held/unresolved protections are
   invariants rather than switches.
5. **Deletion uncertainty:** reuse shared `FailureEvidence` /
   `OutcomeUncertainty` primitives while exposing deletion-specific result and
   reconciliation types.
6. **Top-level exports:** governance types stay in qualified namespaces for the
   full 2.x line; top-level promotion requires a future major-version API
   review.

These decisions close the architecture-review blockers without assigning a
release number or implementation LOT.

---

## 31. Accepted decision

The following architectural direction is accepted:

```text
keep 2.0 DatasetPublisher frozen
        |
        v
add governance contracts
        |
        +--> append-only lifecycle evidence
        +--> CAS publication capability
        +--> provider-specific coordination
        +--> deterministic retention planning
        +--> guarded GC + deletion evidence
        +--> rollback as new publication
        |
        v
provider conformance before roadmap promotion
```

The next artifact is an implementation roadmap derived from this accepted RFC.
Acceptance still does not assign a LOT number or 2.x release target.
