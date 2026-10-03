# PyIngestKit 2.1 — LOT-24 Durable Lifecycle Ledger + PostgreSQL

## Status

**Implemented candidate: 2.1.0a2.**

LOT-24 implements the durable lifecycle ledger defined by RFC-001 while
preserving the exact LOT-23 governance domain and Protocol contracts.

## Scope

LOT-24 adds:

- **MemoryPublicationLedger** as deterministic reference/conformance adapter;
- **PostgresPublicationLedger** as the first durable production ledger;
- canonical persistence of PublicationIntent and lifecycle events;
- append-only event history;
- durable unresolved/resolved operation state;
- restart recovery;
- explicit transaction scopes for atomic register + append;
- secret-bearing evidence rejection before persistence.

LOT-24 does **not** add filesystem CAS, S3 CAS, physical garbage collection,
rollback side effects, scheduler behavior, or modifications to the historical
V1 MetadataStore.

## Frozen LOT-23 contract

LOT-24 does not change the qualified governance namespace or the exact
signatures of:

~~~text
PublicationLedger
ConditionalDatasetPublisher
DatasetVersionGarbageCollector
~~~

The package root remains the exact frozen 2.0 root.

Provider implementations are exposed from explicit adapter namespaces:

~~~python
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.adapters.postgres import PostgresPublicationLedger
~~~

## Durable logical records

The PostgreSQL adapter owns three isolated additive V2 tables:

~~~text
pyingestkit_v2_publication_operation
pyingestkit_v2_publication_event
pyingestkit_v2_version_hold
~~~

These tables are independent from the historical V1 metadata schema.

The operation record preserves operation ID, dataset identity, deterministic
intent fingerprint, request time, canonical PublicationIntent payload and
resolved/terminal state.

The event record preserves a monotonic sequence, unique event ID, optional
operation identity, dataset identity, event type, occurrence time and canonical
lifecycle-event payload.

The version-hold table is created now as required durable structure; hold
mutation APIs remain deferred to LOT-27.

## Portable persistence codec

Ledger payloads use framework-owned canonical V2 boundary contracts rather than
SQLAlchemy objects.

Publication intents persist canonical DatasetVersionReference and
CorrelationContext envelopes. Lifecycle events persist optional
DatasetVersionReference and FailureEvidence envelopes.

Reads reconstruct and revalidate domain objects. Intent fingerprints are
recomputed and compared, so malformed or tampered persisted intent state fails
closed.

## Idempotence

The LOT-23 invariant is now durable:

~~~text
same PublicationOperationId + same semantic intent
    -> return existing operation

same PublicationOperationId + different semantic intent
    -> fail closed
~~~

PostgreSQL uses INSERT ... ON CONFLICT DO NOTHING followed by canonical intent
verification, making registration safe under multi-process races.

## Append-only lifecycle semantics

For events carrying an operation ID:

1. the operation must already exist;
2. the event dataset must match the registered intent;
3. PostgreSQL locks the operation row while appending;
4. terminal events resolve the operation;
5. new event IDs are rejected after resolution;
6. an exact duplicate event remains idempotent.

Publication-outcome-unknown remains unresolved and therefore continues to appear
in list_unresolved() until a terminal reconciliation event is recorded.

## Transaction model

The frozen PublicationLedger Protocol keeps register() and append() separate.
LOT-24 therefore adds an adapter-level explicit transaction context without
changing that Protocol:

~~~python
with ledger.transaction() as transaction:
    transaction.register(intent)
    transaction.append(first_event)
~~~

The transaction-bound PostgreSQL ledger never commits itself.

~~~text
normal context exit
    -> operation + event commit together

exception
    -> operation + event both roll back
~~~

The in-memory adapter provides equivalent observable atomicity using a
rollbackable snapshot.

## Restart recovery

The required durable path is:

~~~text
register intent
    ↓
append non-terminal event
    ↓
close process/adapter
    ↓
new PostgresPublicationLedger
    ↓
get_operation()
list_unresolved()
list_events()
    ↓
same portable evidence
~~~

No provider client or secret is required to reconstruct the operation.

## Concurrent event ordering

PostgreSQL assigns each event a monotonic sequence ID. Concurrent writers may
race for insertion order, but committed history has one deterministic observable
ordering and repeated list_events() calls return that order.

## Secret safety

Lifecycle evidence is validated before durable persistence. The ledger rejects
obvious secret-bearing free text such as URI user-info credentials,
password/secret/token/API-key assignments and bearer-token text.

The PostgreSQL adapter exposes only a password-redacted safe_dsn for
diagnostics.

## Optional dependency isolation

The base package remains provider-neutral. pyingestkit.governance and
MemoryPublicationLedger work without SQLAlchemy or psycopg.

PostgresPublicationLedger remains behind the existing postgres extra:

~~~bash
pip install "pyingestkit[postgres]"
~~~

## Conformance evidence

Shared behavioral contract:

~~~text
tests/conformance/v2/_governance_ledger_contract.py
~~~

Memory qualification:

~~~text
tests/unit/v2/test_memory_publication_ledger.py
~~~

Real PostgreSQL qualification:

~~~text
tests/integration/v2/test_postgres_publication_ledger.py
~~~

The PostgreSQL E2E proves shared semantics, atomic commit/rollback, restart
recovery, stable concurrent ordering, additive table creation and DSN
redaction.

## CI gates

LOT-24 extends postgres-e2e to qualify both PostgresTargetV2 and
PostgresPublicationLedger. The clean base-wheel gate imports
MemoryPublicationLedger while still proving SQLAlchemy and psycopg are absent.

The milestone checker verifies package version 2.1.0a2, the LOT-24 phase,
frozen 2.0 root, frozen LOT-23 governance exports/signatures, exact adapter
inventory, exact PostgreSQL table set and required evidence.

## Next lot

LOT-25 / **2.1.0a3** implements filesystem conditional publication:

~~~text
PublicationSnapshot
    +
PublicationRevision
    +
ConditionalDatasetPublisher
        ↓
atomic filesystem CAS
~~~

LOT-25 must preserve the exact LOT-23 Protocols and LOT-24 ledger semantics.
