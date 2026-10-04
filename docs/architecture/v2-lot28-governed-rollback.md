# PyIngestKit 2.1 — LOT-28 Governed Rollback

**Implemented candidate: 2.1.0b2.**

LOT-28 makes rollback an explicit governed publication of an already-existing
immutable `DatasetVersion`. It does not mutate historical bytes, delete
history, or reinterpret strict replay.

## Scope

LOT-28 adds:

- qualified `pyingestkit.governance.rollback.GovernedRollbackService`;
- provider-neutral rollback admission over the frozen `PublicationIntent`;
- durable `ROLLBACK_REQUESTED` / `ROLLBACK_COMMITTED` lifecycle evidence;
- filesystem rollback through the existing CAS publication adapter;
- S3 rollback through the existing provider-qualified CAS publication adapter;
- stale-revision conflict handling;
- idempotent operation reuse;
- distinct revisions for repeated rollback to the same historical version;
- UNKNOWN_OUTCOME reconciliation without blind republish;
- PostgreSQL restart proof for rollback lifecycle evidence.

LOT-28 does not change:

- the exact PyIngestKit 2.0 package root;
- the LOT-23 `pyingestkit.governance` export set;
- `PublicationLedger`;
- `ConditionalDatasetPublisher`;
- `DatasetVersionGarbageCollector`;
- `DatasetVersionStore`;
- `DatasetPublisher`;
- `PublishedDataset`;
- contract-version 1 portable meanings;
- strict replay semantics.

## Core invariant

Rollback is defined as:

    rollback != version mutation
    rollback != history deletion
    rollback != replay

    rollback =
        new PublicationIntent
        targeting an existing immutable DatasetVersion
        + expected PublicationRevision
        + CAS publication
        + lifecycle evidence

A successful rollback therefore creates a new publication revision even when
the target DatasetVersion is content-identical to the currently published
version.

## Admission

`GovernedRollbackService.rollback(intent)` validates the target before
admitting the lifecycle operation.

The target must:

1. already exist in the configured `DatasetVersionStore`;
2. match the requested dataset/version identity;
3. pass `DatasetVersionStore.read(...)` integrity verification.

If these preconditions fail, the rollback returns a controlled
`ConditionalPublicationStatus.FAILED` with:

    governance.rollback.target_invalid

The operation is not admitted to the lifecycle ledger, so an invalid target
cannot create a permanently unresolved destructive/governance operation.

## Durable request evidence

For a valid target, the service persists atomically when the ledger exposes its
transaction capability:

    PublicationIntent
    +
    ROLLBACK_REQUESTED

The request event records:

- operation ID;
- dataset/version target;
- expected publication revision;
- aware timestamp.

It contains no provider token or credential.

The same `PublicationOperationId` can be retried only with the exact same
intent fingerprint.

An operation already registered as an ordinary publication cannot later be
reinterpreted as rollback.

## CAS execution

After admission, the service delegates to the frozen:

    ConditionalDatasetPublisher.compare_and_publish(intent)

No rollback-specific provider protocol is introduced.

Filesystem therefore keeps its inter-process CAS semantics.

S3 therefore keeps its qualified conditional-write semantics.

Both adapters inspect durable lifecycle history. When the operation contains
`ROLLBACK_REQUESTED`, a successful publication terminates with:

    ROLLBACK_COMMITTED

instead of:

    PUBLICATION_COMMITTED

Ordinary governed publication remains unchanged.

## Concurrency

Rollback obeys the exact same revision fence as ordinary governed publication.

Example:

    R20 / V5
       |
       | actor A observes R20
       |
       +---- actor B publishes V6 ----> R21 / V6
       |
       +---- actor A rollback V3
             expected_revision = R20
                         |
                         v
                     CONFLICT

No provider write is allowed to silently override R21.

## Revision progression

Every successful rollback gets a fresh framework-owned
`PublicationRevision`.

Example:

    R10 / V1
      -> publish V2
    R11 / V2
      -> rollback V1
    R12 / V1
      -> rollback V1 again
    R13 / V1

The two rollback operations remain distinct even though they target the same
immutable DatasetVersion.

This preserves ABA safety.

## Immutable bytes

The rollback service never calls:

    DatasetVersionStore.put(...)

and neither filesystem nor S3 rollback rewrites version objects.

Only the mutable publication pointer changes.

Tests read the target version before and after rollback/conflict and require
equality of the decoded immutable representation.

## UNKNOWN_OUTCOME

Rollback inherits the ordinary governed-publication uncertainty model.

If provider acknowledgement is ambiguous after the pointer may have committed:

    ConditionalPublicationStatus.UNKNOWN_OUTCOME
    FailureCategory.UNKNOWN_OUTCOME
    Retryability.RETRYABLE_AFTER_RECONCILIATION
    OutcomeUncertainty.REQUIRES_RECONCILIATION

The operation remains unresolved.

The caller must use:

    GovernedRollbackService.reconcile(intent)

The service discovers the provider's existing reconciliation capability and
does not invoke `compare_and_publish(...)` again.

If provider truth proves that the rollback pointer committed, reconciliation
emits:

    ROLLBACK_COMMITTED

and resolves the operation.

## PostgreSQL durability

LOT-28 proves a real rollback with `PostgresPublicationLedger`:

    publish V1
      -> publish V2
      -> rollback V1
      -> close ledger
      -> reopen ledger
      -> reload operation
      -> ROLLBACK_REQUESTED
      -> ROLLBACK_COMMITTED
      -> no unresolved operation

No new PostgreSQL table or portable schema version is required.

The existing LOT-24 publication-operation/event records already carry all
required portable evidence.

## Replay boundary

Strict replay remains independent.

`ReplayServiceV2.replay(...)` still invokes the runtime with:

    publish=False

LOT-28 neither imports rollback into replay nor makes replay publish
implicitly.

A future explicit feature may compose replay output with governed publication,
but that is outside LOT-28.

## Qualified namespace

The new public surface is:

    pyingestkit.governance.rollback.GovernedRollbackService

It is deliberately absent from:

    pyingestkit.__all__
    pyingestkit.governance.__all__

This preserves the frozen 2.0 root and LOT-23 governance namespace.

## Executable evidence

LOT-28 adds:

- filesystem rollback success + revision advancement;
- filesystem stale rollback conflict;
- repeated rollback to same historical version;
- invalid/missing target admission rejection;
- filesystem UNKNOWN_OUTCOME reconciliation;
- S3 rollback success and immutable-version proof;
- S3 stale rollback conflict;
- S3 UNKNOWN_OUTCOME reconciliation;
- PostgreSQL restart durability for rollback events;
- strict-replay `publish=False` regression;
- exact LOT-23 Protocol signature regression;
- clean-package qualified rollback import;
- dedicated File/S3 rollback release-blocking CI gates.

Machine fixture:

    tests/contract/fixtures/governance_v2_1_beta2.json

Milestone checker:

    scripts/check_v2_1_beta2.py

## Next lot

LOT-29 / `2.1.0rc1` performs full cross-provider governance conformance,
crash/recovery qualification and release-candidate closure.

No new governance architecture is planned for LOT-29.
