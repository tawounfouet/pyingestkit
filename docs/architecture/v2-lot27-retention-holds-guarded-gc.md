# PyIngestKit 2.1 — LOT-27 Retention, Holds & Guarded Garbage Collection

**Implemented candidate: 2.1.0b1.**

LOT-27 introduces deterministic retention planning and explicit destructive
DatasetVersion lifecycle execution while preserving the immutable-history
safety model established by PyIngestKit 2.0 and the governance contracts frozen
in LOT-23.

## Scope

LOT-27 adds:

- qualified `RetentionState`, `RetentionStateLoader` and `RetentionPlanner`;
- additive `VersionHoldRepository` behavior on Memory/PostgreSQL lifecycle ledgers;
- durable `HOLD_PLACED` and `HOLD_RELEASED` evidence;
- durable `RETENTION_PLAN_CREATED` evidence;
- `FileDatasetVersionGarbageCollector`;
- `S3DatasetVersionGarbageCollector`;
- stale-plan detection before destructive I/O;
- canonical provider binding before deletion;
- deletion uncertainty and provider-truth reconciliation;
- repeat-safe already-absent semantics.

LOT-27 does not modify:

- the exact PyIngestKit 2.0 package root;
- `DatasetVersionStore`;
- `DatasetPublisher`;
- `PublishedDataset`;
- the LOT-23 governance root export set;
- the LOT-23 `PublicationLedger`, `ConditionalDatasetPublisher` or
  `DatasetVersionGarbageCollector` signatures;
- existing contract-version 1 portable meanings.

## Read-only lifecycle capture

Destructive planning starts by capturing one immutable `RetentionState`:

    DatasetVersion inventory
      + governed current publication
      + active version holds
      + unresolved publication/rollback intents
      + integrity-verification outcome

`RetentionStateLoader` may read provider truth, but it performs no destructive
operation.

Every inventoried version is verified through the frozen
`DatasetVersionStore.read(...)` contract. If verification fails, that version
is not marked verified and therefore becomes protected by the planner.

## Pure deterministic planning

`RetentionPlanner.plan(...)` is pure with respect to the captured state.

It applies the following mandatory protections:

1. the current published DatasetVersion;
2. every active `VersionHold`;
3. every version referenced by an unresolved lifecycle operation;
4. every inventoried version whose integrity was not verified;
5. the newest `keep_last` versions;
6. versions younger than `min_age_seconds`;
7. versions without a usable creation timestamp when an age policy is active.

Only versions outside all protection sets become candidates.

The ordering is deterministic:

    created_at DESC
    version_id DESC

A missing creation time sorts behind timestamped versions but is protected when
`min_age_seconds` is enabled because age cannot be proven safely.

## Evidence fingerprint

Every plan contains a deterministic SHA-256 evidence fingerprint over:

- dataset identity;
- plan evaluation timestamp;
- retention policy;
- inventory identities and creation timestamps;
- current publication revision and version;
- active hold identities/timestamps/reasons;
- unresolved operation identities, targets and expected revisions;
- verified version identities.

The fingerprint intentionally excludes provider paths, S3 ETags, credentials
and client details.

The evaluation timestamp is part of the fingerprint so age-policy eligibility
is bound to the instant at which the plan was produced.

## Stale-plan guard

Both physical collectors are bound to one immutable
`GarbageCollectionPlan`.

Before deleting a present candidate they prove:

    request plan_id == bound plan_id
    expected_evidence == plan evidence
    reference is an original plan candidate
    current lifecycle fingerprint == plan evidence

If any protection state changes after planning, including:

- a new hold;
- publication of the candidate;
- a new unresolved operation;
- inventory change;
- integrity-state change;

the current fingerprint differs and deletion fails closed with:

    governance.gc.stale_plan

No provider delete is issued.

Repeat execution after a successful deletion is handled separately: if the
canonical version is already absent and the caller still presents the exact
original plan/evidence/candidate identity, the result is
`ALREADY_ABSENT`. This keeps completed plan replay safe without treating the
expected inventory change caused by the previous deletion as a destructive
authorization bypass.

## Durable holds

Memory and PostgreSQL ledgers implement the additive qualified
`VersionHoldRepository` behavior:

    place_hold(VersionHold)
    release_hold(DatasetVersionReference, released_at=...)
    list_active_holds(dataset_id)

This does not change the frozen `PublicationLedger` Protocol.

PostgreSQL uses the reserved LOT-24
`pyingestkit_v2_version_hold` table. The physical row stores dataset/version
identity, held/released timestamps and reason.

The portable hold value remains provider-neutral.

A hold is lifecycle evidence; it is not S3 Object Lock, a filesystem ACL or a
cloud retention policy.

## Filesystem deletion binding

`FileDatasetVersionGarbageCollector` derives the deletion target only from the
canonical `FileDatasetVersionStore` dataset/version identity.

It rejects:

- foreign DatasetVersionReference locators;
- symlink version directories;
- version directories resolving outside the store root;
- incomplete/corrupt version state;
- stale plans.

The caller never supplies an arbitrary filesystem path to the destructive
operation.

After all checks, the canonical version directory is removed.

## S3 deletion binding

`S3DatasetVersionGarbageCollector` derives exactly two canonical keys from the
bound `S3DatasetVersionStoreV2`:

    datasets/versions/<dataset>/<version>/version.json
    datasets/versions/<dataset>/<version>/snapshot.json

The caller never supplies bucket or key values.

Before deletion, both objects must be either:

- present and integrity-verifiable; or
- both absent for idempotent replay.

A partial pre-existing pair fails closed.

A DatasetVersionReference carrying a foreign locator is rejected even when its
dataset/version identity matches a real stored version.

## Deletion lifecycle evidence

Execution emits append-only lifecycle evidence:

    GC_DELETE_REQUESTED
      -> GC_DELETE_COMMITTED
      -> or GC_DELETE_FAILED
      -> or GC_DELETE_OUTCOME_UNKNOWN

The event metadata binds:

- plan ID;
- expected evidence fingerprint;
- execution/reconciliation phase.

Failure values reuse the shared `FailureEvidence`, `Retryability` and
`OutcomeUncertainty` contracts.

No publication result type is reused for deletion.

## Unknown outcomes and reconciliation

Any exception after provider deletion may have begun is treated conservatively
as:

    DatasetVersionDeletionStatus.UNKNOWN_OUTCOME
    Retryability.RETRYABLE_AFTER_RECONCILIATION
    OutcomeUncertainty.REQUIRES_RECONCILIATION

The caller must invoke `reconcile_delete(...)`.

Filesystem reconciliation observes the canonical version directory.

S3 reconciliation observes both canonical version objects.

Possible results are:

    CONFIRMED_DELETED
    CONFIRMED_PRESENT
    UNKNOWN
    CONFLICT

Reconciliation never blindly executes the delete again.

## PostgreSQL hold restart proof

LOT-27 extends the real PostgreSQL 16 qualification:

    place hold
      -> close ledger
      -> reopen ledger
      -> active hold recovered
      -> release hold
      -> active set empty
      -> HOLD_PLACED / HOLD_RELEASED history preserved

The existing publication-operation and publication-event contracts remain
unchanged.

## Security properties

LOT-27 makes destructive capability narrower than storage capability:

    DatasetVersionStore
        != deletion capability

    DatasetVersionGarbageCollector
        = explicit destructive capability
        + immutable plan binding
        + current evidence guard
        + canonical provider target derivation
        + reconciliation

Filesystem paths and S3 keys are never accepted directly through the frozen
garbage-collector port.

## Executable evidence

LOT-27 includes:

- pure planner tests for `keep_last` and `min_age_seconds`;
- current/hold/unresolved/unverified protections;
- plan-fingerprint drift tests;
- Memory hold lifecycle tests;
- PostgreSQL hold restart/release E2E;
- filesystem delete/idempotence E2E;
- filesystem stale-current protection;
- filesystem symlink/path-escape rejection;
- filesystem unknown-outcome reconciliation;
- S3 delete/idempotence E2E;
- S3 newly-held stale-plan rejection;
- S3 foreign-locator rejection;
- S3 unknown-outcome reconciliation;
- provider/public-contract regression;
- release-blocking filesystem and S3 GC CI gates.

Machine fixture:

    tests/contract/fixtures/governance_v2_1_beta1.json

Milestone checker:

    scripts/check_v2_1_beta1.py

## Next lot

LOT-28 / `2.1.0b2` introduces governed rollback.

Rollback remains a new CAS publication operation targeting an existing immutable
historical DatasetVersion. It does not mutate version bytes and does not delete
history.
