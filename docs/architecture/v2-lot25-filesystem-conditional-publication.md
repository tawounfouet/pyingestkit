# PyIngestKit 2.1 — LOT-25 Filesystem Conditional Publication

**Implemented candidate: 2.1.0a3.**

LOT-25 implements the first provider-correct ConditionalDatasetPublisher for the
local filesystem profile. It preserves every frozen PyIngestKit 2.0 contract and
uses the durable PublicationLedger introduced by LOT-24 without extending the
frozen LOT-23 Protocols.

## Scope

LOT-25 adds:

- FileConditionalDatasetPublisher;
- opaque framework-owned PublicationRevision persistence;
- compare-and-swap publication;
- inter-process filesystem locking;
- ABA-safe revision advancement;
- legacy pointer bootstrap;
- idempotent operation resume;
- explicit CONFLICT semantics;
- UNKNOWN_OUTCOME and reconciliation;
- multiprocess concurrency qualification.

LOT-25 does not change:

- DatasetPublisher;
- DatasetVersionStore;
- PublishedDataset;
- the exact 2.0 package root;
- the LOT-23 governance namespace;
- version-1 portable wire contracts.

## Provider composition

The governed filesystem profile composes three existing responsibilities:

    FileDatasetVersionStore
        |
        +-- immutable DatasetVersion storage
        +-- frozen DatasetPublisher / get_published behavior
        |
        +-- FileConditionalDatasetPublisher
                |
                +-- ConditionalDatasetPublisher
                +-- PublicationLedger
                +-- inter-process lock
                +-- atomic os.replace pointer update

The conditional provider is deliberately separate from FileDatasetVersionStore.
This prevents the ordinary 2.0 publisher from accidentally advertising CAS
correctness.

## Pointer compatibility

The original 2.0 pointer shape remains valid:

    publication_schema
    dataset_id
    version_id
    published_at
    published_from_run_id

A governed publication adds only additive fields:

    governance_revision
    governance_operation_id
    governance_intent_fingerprint

FileDatasetVersionStore.get_published(...) ignores the additive fields and
therefore continues to read governed pointers without any 2.0 contract change.

## Revision model

PublicationRevision remains provider-neutral. Provider-specific filesystem
details such as inode, lock descriptor or file timestamp are never exposed.

Every successful governed publication generates a new framework revision:

    R10 / V1
      -> publish V2
    R11 / V2
      -> publish historical V1
    R12 / V1

R12 is distinct from R10 even though the current DatasetVersion is V1 again.
A writer holding R10 therefore conflicts, preventing ABA.

## Compare-and-swap algorithm

The provider performs the following sequence:

    register durable intent
      -> append PUBLICATION_REQUESTED
      -> acquire dataset-scoped inter-process lock
      -> inspect current pointer and revision
      -> compare current revision with expected revision
      -> verify target immutable DatasetVersion
      -> write temporary governed pointer
      -> atomic os.replace
      -> fsync containing directory where supported
      -> append PUBLICATION_COMMITTED

If the observed revision differs from the expected revision:

    no pointer write
      -> PUBLICATION_CONFLICT
      -> ConditionalPublicationStatus.CONFLICT

Exactly one process can therefore commit from one observed revision.

## Inter-process lock

The lock is an implementation detail and is not exposed through
ConditionalDatasetPublisher.

On POSIX systems the adapter uses flock. On Windows the implementation resolves
the native msvcrt locking primitive lazily. Lock acquisition is non-blocking
with a bounded retry window.

Failure to acquire the lock before the configured timeout occurs before any
provider side effect and returns a controlled known failure.

## Legacy pointer bootstrap

A legacy 2.0 pointer has no governance_revision. During controlled enablement,
inspect derives a deterministic bootstrap revision from the exact pointer bytes.

The required deployment fence is:

    quiesce legacy writers
      -> inspect/bootstrap existing pointer
      -> enable governed publisher
      -> all subsequent writers use governance CAS

The deterministic bootstrap does not claim protection from an unrelated legacy
writer that continues replacing the same pointer. Governance correctness starts
only after the legacy-writer fence has been enforced operationally.

## Operation idempotence

Every compare-and-publish operation is first registered in PublicationLedger.
Reusing a PublicationOperationId with a different intent fingerprint fails
closed through the LOT-24 ledger contract.

The governed pointer also records operation ID and intent fingerprint. If a
caller resumes an operation after provider commit but before durable terminal
ledger evidence, the adapter observes provider truth before any new side effect.

No blind pointer replacement is performed.

## Crash and uncertainty semantics

Before os.replace:

    failure
      -> previous pointer remains readable
      -> known FAILED outcome
      -> operation may be retried according to policy

After os.replace:

    acknowledgement/evidence failure
      -> provider may already contain new pointer
      -> UNKNOWN_OUTCOME
      -> no blind retry
      -> reconcile provider truth

Reconciliation only inspects the pointer. It never republishes.

Possible reconciliation conclusions are:

- committed by the same operation;
- confirmed not committed;
- conflict with another publication.

The durable lifecycle ledger is then closed with the corresponding reconciliation
event when provider truth is known.

## Security and confinement

Dataset identifiers are validated before they are mapped to filesystem paths.
The governed pointer remains under the wrapped FileDatasetVersionStore root.

The provider operation reference contains only a dataset hash and operation ID.
Absolute filesystem paths, credentials and provider secrets are not persisted in
portable lifecycle events.

## Executable qualification

LOT-25 adds evidence for:

- frozen ConditionalDatasetPublisher conformance;
- governed pointer readability through the 2.0 DatasetPublisher reader;
- legacy pointer bootstrap;
- ABA rejection;
- crash before replace;
- acknowledgement loss after replace;
- explicit reconciliation;
- initial two-process race with exactly one winner;
- existing-revision two-process race with exactly one winner.

The milestone machine fixture is:

    tests/contract/fixtures/governance_v2_1_alpha3.json

and the terminal checker is:

    scripts/check_v2_1_alpha3.py

## Compatibility statement

LOT-25 is additive to 2.0 and to LOT-23/LOT-24.

The following remain frozen:

    pyingestkit.__all__
    IngestionRuntime.run(...)
    DatasetPublisher
    DatasetVersionStore
    PublishedDataset
    existing contract-version 1 meanings

FileConditionalDatasetPublisher is exposed only from the explicit provider
namespace:

    pyingestkit.adapters.filesystem

## Next lot

LOT-26 / 2.1.0a4 will implement the same observable CAS semantics for qualifying
S3 endpoints. It must prove real conditional create/replace behavior and must
fail closed when an endpoint cannot provide the required guarantees.
