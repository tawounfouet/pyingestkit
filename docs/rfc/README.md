# PyIngestKit Architecture RFCs

Architecture RFCs evaluate post-stable feature candidates before they become implementation milestones.

## Status model

An RFC uses one of these statuses:

- **Proposed** — under design/review; no roadmap commitment;
- **Accepted** — architecture and acceptance criteria approved; implementation planning may begin;
- **Rejected** — evaluated and intentionally not pursued;
- **Superseded** — replaced by a later RFC.

An accepted RFC is still not automatically a release or LOT commitment. A separate roadmap decision assigns implementation sequencing and versioning.

## Governing rules

Every post-2.0 RFC must:

1. preserve the PyIngestKit product boundary;
2. identify the exact 2.0 stable contracts it touches;
3. prefer additive contracts over modification of frozen 2.0 surfaces;
4. define provider-neutral semantics before provider implementations;
5. specify outcome-uncertainty, idempotency and reconciliation behavior;
6. include executable acceptance criteria before implementation starts;
7. separate framework-owned state from provider-owned state;
8. identify explicit non-goals.

## Current RFCs

- [RFC-001 — Publication & Lifecycle Governance](RFC-001-publication-lifecycle-governance.md) — **Accepted**
  - [Formal architecture review](reviews/RFC-001-architecture-review.md)
