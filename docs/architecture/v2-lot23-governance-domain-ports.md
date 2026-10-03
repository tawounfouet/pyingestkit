# PyIngestKit 2.1 — LOT-23 Governance Domain & Ports

## Status

**Implemented candidate: 2.1.0a1.**

LOT-23 opens the additive PyIngestKit 2.1 feature line established by the
accepted RFC-001 roadmap.

It introduces provider-neutral lifecycle-governance values and ports only.
No PostgreSQL ledger, filesystem CAS, S3 CAS, retention execution, physical
deletion or rollback side effect is implemented in this lot.

## Compatibility baseline

The PyIngestKit 2.0 contract remains frozen and executable.

LOT-23 does not change:

- the 11-symbol `pyingestkit` package root;
- `DatasetPublisher`;
- `DatasetVersionStore`;
- `PublishedDataset`;
- `IngestionRuntime.run(...)`;
- existing version-1 portable wire contracts.

The 2.0 compatibility baseline is checked independently from the current
2.1 milestone version.

## Qualified namespace

All new APIs are opt-in under:

```python
import pyingestkit.governance
```

Nothing from LOT-23 is promoted to the package root.

The qualified namespace exposes:

```text
PublicationOperationId
PublicationRevision
PublicationSnapshot
PublicationIntent
PublicationLifecycleEventType
PublicationLifecycleEvent
ConditionalPublicationStatus
ConditionalPublicationOutcome
RetentionPolicy
VersionHold
GarbageCollectionPlanId
GarbageCollectionPlan
DatasetVersionDeletionStatus
DatasetVersionDeletionResult
DatasetVersionDeletionReconciliationStatus
DatasetVersionDeletionReconciliationResult

PublicationLedger
ConditionalDatasetPublisher
DatasetVersionGarbageCollector
```

The exact export set is frozen in
`tests/contract/fixtures/governance_v2_1_alpha1.json`.

## Publication operation identity

`PublicationOperationId` is UUID-backed and distinct from
`IngestionRunId`, provider request IDs and correlation IDs.

`PublicationIntent` carries:

- operation identity;
- immutable target DatasetVersionReference;
- expected PublicationRevision;
- ingestion run identity;
- CorrelationContext;
- requested timestamp.

Its deterministic `intent_fingerprint` excludes retry-local time while
including the semantic target, expected revision and execution/correlation
identity.

The invariant is executable:

```text
same operation_id + same intent
    -> compatible/idempotent

same operation_id + different intent
    -> fail closed
```

LOT-24 will persist that rule; LOT-23 owns its domain semantics.

## Publication revision

`PublicationRevision` is framework-owned and provider-neutral.

Two forms exist:

```text
initial
rev-<uuid-hex>
```

The revision is intentionally not an S3 ETag, filesystem inode or SQL
transaction identifier.

Every future governed publication will advance to a new framework revision,
which prevents ABA confusion even when content returns to a previously
published DatasetVersion.

## Publication snapshot

`PublicationSnapshot` couples:

```text
dataset_id
publication revision
PublishedDataset | None
```

An unpublished snapshot must use the explicit `initial` revision.
A published snapshot must use a non-initial revision and the dataset identity
must match.

## Lifecycle evidence

`PublicationLifecycleEvent` is portable, append-only evidence input for the
future ledger.

The event vocabulary includes:

- version observed;
- publication requested/committed/conflict/unknown outcome;
- publication reconciliation outcomes;
- rollback requested/committed;
- hold placed/released;
- retention plan created;
- GC delete requested/committed/failed/unknown outcome.

Metadata uses the existing credential-safe validation rules. Credentials,
tokens and secret-like fields fail closed.

No persistence backend is introduced by LOT-23.

## Conditional publication outcome

`ConditionalPublicationOutcome` models:

```text
SUCCEEDED
CONFLICT
FAILED
UNKNOWN_OUTCOME
```

Non-success outcomes require structured `FailureEvidence`.

An unknown outcome must use:

```text
FailureCategory.UNKNOWN_OUTCOME
OutcomeUncertainty.REQUIRES_RECONCILIATION
```

This extends the existing PyIngestKit 2.0 uncertainty vocabulary rather than
creating a competing model.

## Retention contract

The first 2.1 retention policy is deliberately small:

```python
RetentionPolicy(
    keep_last: int >= 1,
    min_age_seconds: int >= 0 | None,
)
```

There is no expression language, tag DSL, scheduling model or provider storage
class policy.

Mandatory protections such as current/held/unresolved versions remain lifecycle
invariants and are not represented as user-disableable switches.

## Holds

`VersionHold` represents explicit protection of an immutable
DatasetVersionReference.

LOT-23 only defines the value. Durable hold events and GC enforcement begin in
later lots.

## Garbage-collection plan

`GarbageCollectionPlan` is immutable plan evidence containing:

- plan identity;
- dataset identity;
- aware creation time;
- retention policy;
- protected versions;
- candidate versions;
- deterministic evidence fingerprint.

Protected and candidate sets must be disjoint and belong to the same dataset.

Planning and deletion are intentionally separate.

## Deletion result contracts

LOT-23 defines operation-specific deletion result types without implementing
deletion.

Deletion reuses shared failure/uncertainty primitives while keeping domain
results distinct from publication results.

This preserves:

```text
shared uncertainty vocabulary
!=
generic side-effect result model
```

## Additive ports

### PublicationLedger

Exact LOT-23 methods:

```text
register(intent)
append(event)
get_operation(operation_id)
list_operations(dataset_id)
list_unresolved(dataset_id=None)
```

LOT-24 implements Memory and PostgreSQL adapters.

### ConditionalDatasetPublisher

Exact LOT-23 methods:

```text
inspect(dataset_id)
compare_and_publish(intent)
```

LOT-25 and LOT-26 implement provider semantics.

### DatasetVersionGarbageCollector

Exact LOT-23 methods:

```text
delete(reference, *, plan_id, expected_evidence, requested_at)
reconcile_delete(reference, *, plan_id, reconciled_at)
```

No implementation exists in LOT-23. Physical deletion begins in LOT-27.

## Provider neutrality

The governance domain and ports must not import:

- boto3 / botocore;
- SQLAlchemy / psycopg;
- HTTP/provider SDKs;
- Pandas/Polars/PyArrow;
- provider adapters.

The architecture suite enforces this boundary.

## Package/release-line qualification

The repository package version becomes:

```text
2.1.0a1
```

The published stable release remains `v2.0.0`.

CI therefore has two independent checks:

```text
Frozen 2.0 compatibility
        +
Current LOT-23 milestone contract
```

A 2.1 alpha build must never weaken the 2.0 compatibility proof merely because
the current package version is newer.

## Acceptance evidence

LOT-23 is complete when:

- governance namespace export fixture passes;
- exact new Protocol signatures pass;
- package root remains exact 2.0 root;
- existing frozen Protocols/runtime/wire contracts remain exact;
- domain invariants and malformed-input negatives pass;
- operation intent reuse fails closed;
- retention policy validation is deterministic;
- governance domain/ports have no provider imports;
- no governance provider adapter exists;
- Python 3.11–3.14 matrices pass;
- Ruff/format/mypy pass;
- Bandit/pip-audit pass;
- clean wheel/sdist install works without optional providers;
- CI, Security and Docs pass on exact LOT-23 head.

## Next lot

LOT-24 / `2.1.0a2` will implement the durable lifecycle ledger:

```text
PublicationLedger
    ├── Memory reference adapter
    └── PostgreSQL durable adapter
```

It must preserve the exact domain and Protocol baseline frozen by LOT-23.
