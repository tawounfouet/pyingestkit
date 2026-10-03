# PyIngestKit — Post-2.0 Scope Review

## Status

**Scope review only — no roadmap commitment.**

This document reconciles the work explicitly deferred during the V2 architecture
line against the capabilities actually delivered by PyIngestKit 2.0.0.

It exists because the accepted product-scope rule is explicit: a technically
interesting capability does not become a roadmap commitment merely because it
is possible. A future milestone must first pass scope review.

Stable baseline:

```text
PyIngestKit 2.0.0
commit 449ec4c7a92b7a946d63e167e20f3dab1bd5d21c
LOT-22
```

Publication of the exact stable tag/release is tracked separately in issue #51.

---

## 1. Governing rules after 2.0.0

### 2.0.x maintenance line

A 2.0.x release may contain:

- blocker and correctness fixes;
- security fixes;
- documentation corrections;
- provider compatibility fixes;
- performance improvements that preserve observable contracts;
- internal refactoring that preserves the stable root, Protocols and wire
  contracts.

A 2.0.x release must not:

- change the 11-symbol stable package root;
- reshape a frozen provider Protocol;
- change an existing boundary contract version or meaning;
- reintroduce V1 Job/Pipeline/Step aliases into the 2.0 root;
- widen PyIngestKit into orchestration, IAM, catalog, GUI or cloud provisioning.

### Future 2.x feature line

Any additive 2.x feature must preserve the 2.0 compatibility baseline and must
have an explicit architecture contract, executable acceptance criteria and a
provider-neutral core story before implementation starts.

---

## 2. Deferred items already resolved before 2.0.0

Several earlier architecture documents contain “Deferred” sections that are no
longer open work.

| Earlier deferral | Resolution |
| --- | --- |
| strict replay | LOT-11 |
| S3/object-storage DatasetVersion adapters | LOT-15 |
| cross-host S3 replay qualification | LOT-15 + LOT-19 |
| HTTP provider moved behind an optional extra | LOT-21 package cut |
| V1 semantic migration | LOT-18 |
| provider/port conformance matrix | LOT-19 |
| full Customer 360 application E2E | LOT-20 |
| canonical root promotion | LOT-21 |
| wheel/sdist and clean-install qualification | LOT-21 / LOT-22 |
| stable provider/root/wire freeze | LOT-21 / LOT-22 |

These items must not be duplicated in a post-2.0 roadmap.

---

## 3. Open core candidates

The following concerns are still genuinely open and remain compatible with the
defined responsibility of PyIngestKit: reliable ingestion lifecycle,
governance, durable evidence, versioning, publication and replay.

### 3.1 Publication and dataset lifecycle governance

Still open from LOT-08 / LOT-15:

- SQL metadata persistence for V2 lifecycle evidence;
- distributed publication locking;
- compare-and-swap publication semantics;
- retention and garbage collection;
- rollback UX / governed rollback semantics.

This is the strongest candidate for the first post-2.0 architecture RFC because
it deepens existing V2 invariants without expanding PyIngestKit into a new
product category.

A future proposal must preserve:

```text
physical write != governed publication
DatasetVersion = immutable
PublishedDataset = explicit pointer
UNKNOWN_OUTCOME = reconciliation required
```

### 3.2 Replay provenance and historical reconstruction

Still open from LOT-11:

- automatic source-run metadata lookup;
- historical IngestionDefinition restoration;
- parameter override restoration/redaction;
- SQL replay-lineage persistence;
- explicit replay publication.

CLI replay UX is not automatically part of this scope because the V1 CLI was
not promoted into the 2.0 stable Python contract.

A future replay RFC must keep:

```text
replay != live reacquisition
new replay run id != source run id
exact RAW integrity evidence is mandatory
publication after replay is explicit
```

### 3.3 PostgreSQL target semantics

Still open from LOT-14:

- target-load history and durable idempotency metadata;
- explicit table creation/schema-management contracts;
- UPSERT / MERGE modes;
- staging-table semantics;
- replay-specific target suppression.

“Runtime target orchestration” must be split from target semantics. Direct
materialization belongs to PyIngestKit; multi-step orchestration belongs to an
external workflow layer unless a future ADR proves otherwise.

### 3.4 Advanced HTTP acquisition

Still open from LOT-13:

- POST/PUT acquisition semantics;
- OAuth/token refresh orchestration at the provider boundary;
- proxy configuration;
- stronger DNS/IP-level SSRF enforcement;
- asynchronous HTTP acquisition;
- persisted SQL HTTP provenance;
- provider-specific authentication plugins.

Each item requires explicit secret/redaction and retry/uncertainty semantics.
None should be introduced as implicit behavior of the current GET-oriented
connector.

### 3.5 Runtime execution enhancements

Still open from LOT-10:

- framework-owned automatic retry policy;
- asynchronous execution.

These are candidates only if they preserve idempotency and
OutcomeUncertainty. A retry abstraction must never turn an uncertain provider
outcome into an automatic duplicate side effect.

---

## 4. Explicitly outside PyIngestKit core

The following remain outside the core unless a future accepted ADR changes the
product boundary:

- distributed scheduling;
- worker fleets / queue systems;
- generic DAG orchestration;
- reintroduction of Job/Pipeline/Step as a PyIngestKit execution model;
- PyWorkflowKit orchestration implementation;
- provider-specific cloud provisioning;
- bucket lifecycle/replication administration;
- IAM/KMS policy orchestration;
- organization-wide RBAC;
- data catalog/control-plane ownership;
- GUI/SaaS administration;
- AI-agent/RAG/ML workflow ownership;
- streaming/distributed processing engines.

PyIngestKit may expose portable contracts consumed by sibling frameworks. It
must not absorb those sibling responsibilities merely to simplify one example.

---

## 5. Not roadmap features by themselves

Some deferred items are implementation or provider-operability concerns rather
than product milestones:

- multipart-upload tuning;
- low-level provider SDK tuning;
- internal storage optimizations;
- implementation-specific connection pooling.

They may evolve behind stable contracts when evidence justifies them.

---

## 6. Recommended first RFC candidate

### Publication & Lifecycle Governance

**Recommendation only — not yet a milestone.**

The candidate is now materialized as
[RFC-001 — Publication & Lifecycle Governance](../rfc/RFC-001-publication-lifecycle-governance.md)
with status **Accepted** after the
[formal architecture review](../rfc/reviews/RFC-001-architecture-review.md).
Acceptance authorized implementation planning. The derived
[PyIngestKit 2.1.0 implementation roadmap](rfc001-publication-lifecycle-implementation-roadmap.md)
now assigns LOT-23 through LOT-30 and the additive 2.1.0 release line.

The first post-2.0 RFC evaluates a cohesive lifecycle-governance slice:

```text
DatasetVersion
    |
    +--> durable lifecycle metadata
    |
    +--> atomic/CAS publication
    |
    +--> retention policy
    |
    +--> garbage-collection evidence
    |
    +--> explicit rollback
```

Why this is the strongest first candidate:

1. it extends already-stable V2 concepts rather than adding a new domain;
2. it strengthens production safety around publication and long-lived stores;
3. it provides a natural foundation for richer replay lineage later;
4. it can be designed provider-neutrally before File/S3/PostgreSQL adapters;
5. it avoids crossing into orchestration or infrastructure provisioning.

Before implementation, the RFC must answer:

- what is framework-owned state versus provider-owned state;
- what is immutable versus mutable;
- how publication CAS behaves after UNKNOWN_OUTCOME;
- how retention interacts with published/current versions;
- how deletion/GC evidence is persisted;
- whether rollback means pointer movement, new publication event, or both;
- how distributed lock failure is represented;
- how File/S3/PostgreSQL implementations prove equivalent semantics.

---

## 7. Candidate sequence for discussion

This sequence is a review order, **not an approved roadmap**:

```text
RFC-A  Publication & Lifecycle Governance
  -> CAS / locks / retention / GC / rollback

RFC-B  Replay Lineage & Historical Reconstruction
  -> metadata lookup / definition restoration / replay publication

RFC-C  PostgreSQL Target Expansion
  -> idempotency history / staging / UPSERT-MERGE / schema contracts

RFC-D  Advanced HTTP Acquisition
  -> methods / OAuth / proxy / SSRF hardening / async

RFC-E  Runtime Retry / Async Model
  -> only after uncertainty and idempotency rules are proven
```

Each RFC should be accepted or rejected independently.

---

## 8. Exit criteria for this scope review

This review is complete when:

- historical deferrals are reconciled against the 2.0 implementation;
- already-delivered items are removed from future planning;
- out-of-core concerns remain explicitly outside the framework;
- the first candidate RFC is identified without being treated as committed;
- no 2.0 stable contract is modified by the review itself.

No code change is implied by this document.
