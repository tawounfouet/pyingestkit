# RFC-001 — Formal Architecture Review

**Decision:** Accepted  
**Review date:** 2026-10-03  
**Reviewed RFC:** [RFC-001 — Publication & Lifecycle Governance](../RFC-001-publication-lifecycle-governance.md)  
**Stable compatibility baseline:** PyIngestKit 2.0.0

## 1. Review objective

This review determines whether RFC-001 has resolved enough architecture
questions to authorize implementation planning without changing the frozen
PyIngestKit 2.0 contract.

Acceptance here means:

- the architecture direction is approved;
- implementation planning may begin;
- the RFC may be used to derive executable slices and acceptance gates.

Acceptance does **not**:

- create LOT-23;
- assign a 2.x version;
- modify the 2.0 stable package root;
- authorize implementation before the derived roadmap is reviewed.

## 2. Compatibility review

RFC-001 is compatible with the 2.0 baseline because it keeps the existing
stable surfaces unchanged:

- `DatasetPublisher`;
- `DatasetVersionStore`;
- `PublishedDataset`;
- `IngestionRuntime.run(...)`;
- the 11-symbol top-level package root;
- existing version-1 portable wire contracts.

New lifecycle capabilities are additive and remain in qualified namespaces.

**Result:** PASS.

## 3. Product-boundary review

The RFC deepens publication/version lifecycle governance without introducing:

- scheduling;
- worker fleets;
- generic DAG orchestration;
- IAM/KMS administration;
- cloud provisioning;
- catalog/control-plane ownership;
- provider lifecycle administration.

Retention/GC operates on PyIngestKit-owned DatasetVersion lifecycle semantics,
not provider infrastructure policies.

**Result:** PASS.

## 4. Concurrency and uncertainty review

The RFC correctly chooses compare-and-swap as the portable concurrency
correctness primitive.

Provider mechanisms remain internal:

- filesystem inter-process coordination;
- S3 ETag conditional writes;
- SQL row revisions.

Distributed locks are optional implementation mechanisms, not the public
correctness contract.

The existing 2.0 uncertainty rules remain authoritative:

```text
UNKNOWN_OUTCOME
    -> reconciliation required
    -> no blind retry
```

**Result:** PASS.

## 5. Resolution of the six review questions

### Decision D1 — first lifecycle ledger backends

The first implementation line SHALL provide:

1. a provider-neutral `PublicationLedger` Protocol;
2. an in-memory reference adapter for unit tests and conformance;
3. PostgreSQL as the first durable production ledger.

A second durable local backend is **not required in the first implementation
line**.

Rationale:

- PostgreSQL is the durable production target already qualified in the V2
  ecosystem;
- an in-memory adapter is sufficient to test the domain/service contract;
- adding SQLite/filesystem durability immediately would expand the first slice
  without improving distributed publication correctness;
- a local durable adapter may be added later behind the same Protocol if a
  concrete developer workflow requires it.

This decision does not reuse or expand the historical V1 `MetadataStore`
contract.

### Decision D2 — minimum S3 CAS profile

An S3-compatible endpoint may advertise the future conditional publication
capability only when conformance proves all of the following for the publication
pointer key:

1. object inspection exposes a revision token suitable for a conditional write;
2. initial creation supports `If-None-Match: *` or an equivalent atomic
   create-if-absent primitive;
3. replacement supports `If-Match: <current revision token>` or an equivalent
   atomic compare-and-replace primitive;
4. stale conditions are distinguishable from provider/internal failures;
5. concurrent writers are proven to yield one winner for one expected revision;
6. acknowledgement-loss scenarios are reconcilable through provider truth.

For AWS S3, the qualified profile maps naturally to conditional `PutObject`
with `If-None-Match` and `If-Match`.

Official references:

- https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html

The framework MUST NOT infer CAS support merely because an endpoint is described
as “S3-compatible”.

### Decision D3 — holds/pins

Explicit version holds/pins SHALL be included in the first retention/GC
implementation slice.

They are not required for the earlier publication-ledger or CAS slices.

The minimum lifecycle operations are:

```text
HOLD_PLACED
HOLD_RELEASED
```

A held version is never GC-eligible.

Rationale: destructive lifecycle management needs an explicit operator safety
override from its first release.

### Decision D4 — minimum retention policy

The first stable retention policy SHALL remain intentionally small:

```text
RetentionPolicy
  keep_last: int >= 1
  min_age_seconds: int >= 0 | None
```

Mandatory protections are invariants, not configurable policy switches:

- current published version is always protected;
- held versions are always protected;
- versions referenced by unresolved lifecycle operations are always protected.

The first policy explicitly excludes:

- expression languages;
- arbitrary predicates;
- provider storage classes;
- size-based tiering;
- tag-query DSLs;
- cron/scheduling semantics.

This keeps retention deterministic, testable and explainable.

### Decision D5 — deletion uncertainty model

Deletion SHALL reuse the generic 2.0 failure primitives:

- `FailureEvidence`;
- `FailureCategory`;
- `Retryability`;
- `OutcomeUncertainty`.

However, deletion SHALL have operation-specific result types rather than reuse
publication result types.

Conceptually:

```text
DatasetVersionDeletionResult
DatasetVersionDeletionReconciliationResult
```

Rationale:

- uncertainty vocabulary should remain shared across PyIngestKit;
- publication and destructive deletion have different domain outcomes and
  evidence;
- a single generic “side effect result” would erase important semantics.

### Decision D6 — top-level API promotion

Governance types SHALL remain in explicit qualified namespaces throughout the
2.x line.

They SHALL NOT be added to the frozen 2.0 top-level root.

A future top-level promotion requires a new major-version API review.

Rationale:

- the stable 2.0 root is deliberately exact and compact;
- qualified namespaces allow additive feature delivery without rewriting that
  compatibility baseline;
- implementation maturity can evolve without prematurely widening the ergonomic
  root.

## 6. Accepted provider-neutral contract direction

The implementation roadmap may now assume this architecture:

```text
DatasetVersionStore                    (2.0 frozen)
DatasetPublisher                       (2.0 frozen)
        |
        +---------------------------------------------+
        |                                             |
        v                                             v
PublicationLedger                         ConditionalDatasetPublisher
        |                                             |
        +----------------------+----------------------+
                               |
                               v
                    LifecycleGovernanceService
                               |
               +---------------+---------------+
               |                               |
               v                               v
       RetentionPlanner              DatasetVersionGarbageCollector
               |                               |
               v                               v
     GarbageCollectionPlan              deletion evidence
```

Names remain subject to implementation-level naming review, but the
responsibilities and boundaries are accepted.

## 7. Required implementation ordering

The architecture review requires the implementation roadmap to preserve this
dependency order:

```text
A. domain values + additive ports
        ↓
B. ledger + PostgreSQL durability
        ↓
C. filesystem CAS
        ↓
D. S3 CAS capability + endpoint conformance
        ↓
E. retention + holds + GC
        ↓
F. rollback
        ↓
G. cross-provider conformance / crash-recovery qualification
```

Slices may be split further, but later slices must not silently weaken earlier
invariants.

## 8. Release and roadmap constraint

RFC acceptance does not select a release number.

The implementation roadmap must separately decide:

- number of implementation LOTs;
- alpha/beta/RC sequencing, if any;
- release-line target;
- release-blocking conformance gates.

Until that roadmap is accepted, labels such as `LOT-23` or `2.1.0` remain
unassigned.

## 9. Acceptance criteria review

| RFC acceptance criterion | Review |
| --- | --- |
| frozen 2.0 contracts unchanged | PASS |
| CAS is concurrency primitive | PASS |
| durable idempotent operation identity | PASS |
| UNKNOWN_OUTCOME reconciled before retry | PASS |
| no XA/distributed transaction required | PASS |
| rollback is a new governed publication | PASS |
| retention planning separated from deletion | PASS |
| current/held/unresolved versions protected | PASS |
| deletion uncertainty explicit | PASS |
| provider behavioral conformance required | PASS |
| infrastructure administration out of scope | PASS |

## 10. Final decision

**RFC-001 is ACCEPTED.**

The next artifact is an implementation roadmap derived from the accepted RFC.

That roadmap must remain additive to PyIngestKit 2.0 and must provide executable
acceptance gates before code implementation begins.
