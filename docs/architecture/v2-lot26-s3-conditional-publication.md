# PyIngestKit 2.1 — LOT-26 S3 Conditional Publication

**Implemented candidate: 2.1.0a4.**

LOT-26 adds provider-enforced conditional publication for S3 endpoints that
prove the required compare-and-swap profile. It preserves the frozen PyIngestKit
2.0 root, the LOT-23 governance Protocols and the historical
`S3DatasetVersionStoreV2.publish(...)` blind-replace behavior.

## Scope

LOT-26 adds:

- `S3ConditionalDatasetPublisher`;
- endpoint capability qualification before governed publication is exposed;
- atomic create-if-absent with `If-None-Match: *`;
- atomic compare-and-replace with `If-Match: <ETag>`;
- provider-precondition conflict mapping;
- framework-owned ABA-safe `PublicationRevision` values;
- acknowledgement-loss `UNKNOWN_OUTCOME`;
- provider-truth reconciliation without republishing;
- cross-client concurrent race qualification.

LOT-26 does not change:

- `DatasetPublisher`;
- `DatasetVersionStore`;
- `PublishedDataset`;
- the exact 2.0 package root;
- the LOT-23 governance namespace or Protocol signatures;
- portable contract-version 1 meanings.

## Provider boundary

The existing store remains valid for ordinary S3 publication:

    S3DatasetVersionStoreV2.publish(...)
        -> unconditional current.json replacement

Governed publication is a separate capability:

    S3ConditionalDatasetPublisher
        -> inspect current pointer
        -> framework PublicationRevision
        -> internal provider ETag
        -> conditional PutObject

The provider ETag never becomes a `PublicationRevision`, lifecycle event field
or portable provider operation reference.

## Endpoint qualification

Construction of `S3ConditionalDatasetPublisher` performs a destructive but
self-cleaning capability probe under a unique governance probe key.

The probe proves:

1. first `If-None-Match: *` creation succeeds;
2. a second create-if-absent on the same key is rejected;
3. the accepted object is readable together with a provider ETag;
4. `If-Match` replacement using the observed ETag succeeds;
5. repeating replacement with the stale ETag is rejected;
6. provider truth after replacement matches the acknowledged result.

The probe object is deleted in a finally path.

An endpoint that ignores the conditional headers, cannot expose a usable ETag,
or cannot distinguish conditional failure is rejected with
`S3ConditionalWriteCapabilityErrorV2`.

There is no optimistic read-then-write emulation.

## CAS algorithm

For an unpublished dataset:

    inspect -> no pointer
      -> verify expected revision == initial
      -> PutObject If-None-Match: *
      -> exactly one writer can create current.json

For an existing publication:

    GET current.json
      -> read portable framework revision
      -> retain provider ETag internally
      -> verify expected framework revision
      -> PutObject If-Match: observed ETag

Two independent clients that inspect the same provider token can both reach the
write boundary, but the endpoint decides the winner. The loser is mapped to:

    ConditionalPublicationStatus.CONFLICT

with failure code:

    governance.s3.provider_precondition_conflict

## ABA safety

The pointer stores an additive framework-owned field:

    governance_revision = rev-<uuid>

A new revision is generated for every governed commit, even when the target
DatasetVersion returns to an older content identity.

Provider ETags are only transport-level CAS tokens. Portable ABA safety is
owned by `PublicationRevision`.

## Pointer compatibility

Governed S3 pointers retain all existing 2.0 fields:

    publication_schema
    dataset_id
    version_id
    published_at
    published_from_run_id

and add:

    governance_revision
    governance_operation_id
    governance_intent_fingerprint

`S3DatasetVersionStoreV2.get_published(...)` ignores the additive fields and
continues to read the pointer unchanged.

## Legacy pointer bootstrap

An existing 2.0 S3 pointer has no framework governance revision.

The governed publisher derives a deterministic bootstrap revision from the exact
pointer bytes while retaining the observed ETag internally for the first
conditional replacement.

As with filesystem governance, operators must quiesce legacy blind writers
before enabling the governed path.

## Failure semantics

A provider precondition failure is a known conflict.

A non-precondition failure while issuing a conditional write is treated
conservatively as:

    UNKNOWN_OUTCOME
      -> RETRYABLE_AFTER_RECONCILIATION
      -> provider truth must be inspected before retry

An injected acknowledgement loss after a successful provider write follows the
same rule.

Reconciliation never republishes. It only observes current provider truth and
closes the durable lifecycle operation as committed, not committed or conflict.

## Cross-client qualification

The CI proof uses two independently constructed S3 clients against the same
remote endpoint.

A synchronization barrier pauses both governed publishers immediately before
their conditional write. This guarantees that both have already inspected the
same pointer state.

The required outcomes are:

    initial race:
      succeeded = 1
      conflict  = 1

    existing-revision race:
      succeeded = 1
      conflict  = 1

The loser must carry the provider-precondition conflict failure code, proving
that the endpoint conditional write rather than a local pre-check arbitrated the
race.

## Optional dependency boundary

The base package still does not import boto3.

`create_s3_client_v2(...)` keeps boto3 lazy behind the existing `[s3]` extra.
The provider Protocol itself remains dependency-neutral.

## Executable evidence

LOT-26 adds:

- provider contract regression;
- fail-closed unsupported-endpoint qualification;
- initial cross-client race;
- existing-revision cross-client race;
- provider-precondition conflict mapping;
- acknowledgement-loss and reconciliation proof;
- ETag non-leakage assertion;
- governed-pointer compatibility with the frozen S3 reader;
- dedicated release-blocking S3 CAS CI gate.

Machine fixture:

    tests/contract/fixtures/governance_v2_1_alpha4.json

Milestone checker:

    scripts/check_v2_1_alpha4.py

## Next lot

LOT-27 / 2.1.0b1 introduces retention, holds and guarded garbage collection.
Destructive deletion capability remains separate from both the frozen
DatasetVersionStore and the conditional publication ports.
