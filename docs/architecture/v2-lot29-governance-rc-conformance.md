# PyIngestKit 2.1 — LOT-29 Full Governance Conformance & RC

**Candidate: 2.1.0rc1.**

LOT-29 introduces no new governance architecture. It freezes and qualifies the
complete 2.1 publication-lifecycle contract implemented by LOT-23 through
LOT-28.

## Scope

The release candidate proves, on one final head:

- the frozen 2.0 package root and stable contracts remain unchanged;
- the LOT-23 governance namespace and Protocol signatures remain unchanged;
- Memory and PostgreSQL lifecycle ledgers preserve the same portable behavior;
- filesystem conditional publication remains process-safe and ABA-safe;
- S3 conditional publication remains provider-enforced and endpoint-qualified;
- File/S3 retention and guarded GC preserve current/held/unresolved versions;
- File/S3 governed rollback preserves immutable DatasetVersion history;
- crash/restart windows reconcile from observable provider truth;
- built wheel/source artifacts preserve optional-provider isolation;
- security negatives remain fail-closed.

## No new architecture

LOT-29 MUST NOT add:

- a new governance port;
- a new root export;
- a new lifecycle domain concept;
- a new scheduler/orchestrator responsibility;
- a new provider-specific token in portable contracts.

The implementation delta is therefore limited to:

- cross-provider executable evidence;
- RC contract fixture/checker;
- release-blocking CI aggregation;
- built-artifact provider-extra qualification;
- release-candidate documentation/version metadata.

## RC topology

The two composed provider profiles are:

    PostgreSQL PublicationLedger
            +
    FileConditionalDatasetPublisher
            +
    FileDatasetVersionStore

and:

    PostgreSQL PublicationLedger
            +
    S3ConditionalDatasetPublisher
            +
    S3DatasetVersionStoreV2

Both must expose the same portable lifecycle semantics.

## Crash window A — durable intent before provider side effect

The test deliberately persists:

    PublicationIntent
    +
    PUBLICATION_REQUESTED

then simulates process termination before the provider is invoked.

After restart:

    list_unresolved(dataset)
        -> exact intent

Provider reconciliation inspects real provider truth.

Because no provider commit occurred:

    publication revision == expected revision
        ->
    PUBLICATION_RECONCILED_NOT_COMMITTED
        ->
    controlled FAILED outcome
        ->
    operation no longer unresolved

No synthetic success is permitted.

## Crash window B — provider commit before terminal ledger append

The test uses a ledger wrapper around the real PostgreSQL ledger.

The wrapper persists request evidence normally, but raises `SystemExit` when
the publisher attempts its terminal committed event.

`SystemExit` is intentional: it models process death and is not captured by
the application-level `Exception` uncertainty handlers.

Observable sequence:

    durable PUBLICATION_REQUESTED
        ->
    File/S3 provider CAS commit
        ->
    process death before terminal ledger append
        ->
    PostgreSQL restart
        ->
    unresolved intent recovered
        ->
    provider pointer inspected
        ->
    operation-id / intent fingerprint match
        ->
    PUBLICATION_RECONCILED_COMMITTED

The provider pointer is asserted before restart. The test never manufactures a
successful outcome without observable provider truth.

## Retention after recovery

After reconciliation, the restarted PostgreSQL ledger is also used as the hold
repository.

The RC scenario creates three immutable versions:

    V0 old
    V1 historical
    V2 current

Then:

    hold(V0)
    keep_last = 1

Expected plan:

    V2 -> protected because current / newest
    V0 -> protected because held
    V1 -> candidate

This proves retention planning consumes the same recovered lifecycle state used
by publication/reconciliation.

## Rollback after recovery

The hold on V0 is released and the same restarted provider stack executes a
governed rollback to V0 using the current publication revision.

Required terminal history:

    ROLLBACK_REQUESTED
    ROLLBACK_COMMITTED

The historical DatasetVersion remains immutable and rollback advances the
publication revision through the existing CAS provider.

## Fault-injection matrix

LOT-29 closes the full matrix by aggregating prior executable evidence plus the
new mixed-provider crash tests.

| Fault | Evidence |
| --- | --- |
| durable intent before provider side effect | LOT-29 File/S3 + PostgreSQL cross-provider tests |
| provider commit before terminal ledger append | LOT-29 File/S3 + PostgreSQL cross-provider tests |
| acknowledgement loss | LOT-25/26 publication + LOT-28 rollback tests |
| stale revision | LOT-25/26 CAS + LOT-28 rollback |
| filesystem lock acquisition failure | filesystem CAS conformance |
| stale GC plan | LOT-27 File/S3 GC |
| delete acknowledgement loss | LOT-27 File/S3 GC |
| restart with unresolved operation | LOT-24 PostgreSQL + LOT-29 mixed-provider tests |

## Release-blocking governance jobs

LOT-29 adds the explicit jobs required by the accepted roadmap:

    governance-contract
    governance-postgres-e2e
    governance-filesystem-cas
    governance-s3-cas
    governance-gc-e2e
    governance-rollback-e2e
    governance-cross-provider-e2e
    governance-built-artifact
    governance-security-negatives

The existing 2.0 compatibility/release jobs remain mandatory and are not
replaced.

## Built-artifact qualification

The RC is qualified from generated distributions, not only editable source.

Required clean environments:

    wheel base
    wheel + postgres
    wheel + s3
    source distribution base

The base wheel must not leak optional dependencies.

The provider-extra wheel environments must import their concrete adapters from
the installed artifact and preserve the exact 2.0 root.

## Security negatives

The RC release-blocking security job aggregates the established fail-closed
evidence for:

- lifecycle secret rejection;
- credential-bearing references;
- PostgreSQL DSN redaction;
- filesystem path/symlink escape;
- foreign S3 bucket/prefix deletion attempts;
- malformed governance revisions;
- operation-ID reuse with changed intent;
- stale destructive lifecycle evidence;
- unsupported S3 conditional-write capability.

## RC compatibility freeze

The following remain unchanged from the 2.1 feature baseline:

    PublicationLedger
    ConditionalDatasetPublisher
    DatasetVersionGarbageCollector

The following remain unchanged from 2.0:

    pyingestkit.__all__
    DatasetPublisher
    DatasetVersionStore
    PublishedDataset
    IngestionRuntime.run(...)
    contract-version 1 meanings
    v1.0.0 historical tag

The RC checker is:

    scripts/check_v2_1_rc1.py

The machine fixture is:

    tests/contract/fixtures/governance_v2_1_rc1.json

## Stable promotion

LOT-30 may promote this exact qualified contract to `2.1.0`.

LOT-30 is promotion-only. Any semantic, signature or provider-capability change
found necessary after RC qualification must return to a pre-stable candidate
rather than being hidden inside stable promotion.
