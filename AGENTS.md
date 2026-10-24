# AGENTS.md

# PyIngestKit — Repository Instructions for Coding Agents

This file defines the canonical repository-level instructions for AI coding agents and automated contributors working on PyIngestKit.
It applies to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory.

Human-maintained specifications, public contracts, tests, and release evidence remain authoritative over agent assumptions.

---

## 1. Repository Identity

```text
Project: PyIngestKit
Package: pyingestkit
Repository: tawounfouet/pyingestkit
Current stable baseline: 2.1.0
Current milestone: LOT-30 Stable
Python support: 3.11 / 3.12 / 3.13 / 3.14
Build tool: setuptools / wheel
```

PyIngestKit is a focused Python framework for reliable, traceable and replayable batch ingestion.

Canonical V2 execution model:
```text
IngestionDefinition (Source, Decoders, ValidationRules, PublicationTarget)
        ↓
IngestionRuntime.run(...)
        ↓
Durable RAW Acquisition Evidence
        ↓
Immutable DatasetVersion
        ↓
Explicit Conditional Publication (CAS via Ledgers)
        ↓
PublishedDataset & IngestionResult
```

---

## 2. Chain of Authority

When resolving ambiguity or handling test regressions, agents MUST follow this strict hierarchy:

```text
1. RFC specifications (docs/rfc/) and Release evidence (docs/releases/)
2. Contract fixtures and Wire schemas (tests/contract/fixtures/)
3. Architecture test suites (tests/architecture/)
4. AGENTS.md (this file)
5. CLAUDE.md
6. Agent assumptions / LLM training weights
```

---

## 3. Non-Negotiable Architecture Invariants

### Invariant 1: Frozen 2.x Package Root
The package root MUST remain strictly limited to the 11 frozen symbols:
```python
from pyingestkit import (
    ArtifactReference,
    DatasetVersion,
    DatasetVersionReference,
    IngestionDefinition,
    IngestionResult,
    IngestionRun,
    IngestionRunId,
    IngestionRuntime,
    PublishedDataset,
    ResourceReference,
    Source,
)
```
- The canonical synchronous execution entry point is `IngestionRuntime.run(...)`.
- DO NOT reintroduce or alias V1 `Job`, `Pipeline`, `Step`, or `Runner` into the 2.x root.
- Governance APIs remain additive under qualified namespaces (`pyingestkit.governance.*`).

### Invariant 2: RFC-001 Lifecycle Governance & Compare-and-Swap (CAS)
- Publication is ALWAYS compare-and-swap (CAS), never blind overwrite.
- Exactly one writer succeeds for the same expected revision (`expected_revision`).
- Framework-owned publication revisions prevent ABA; provider ETags/tokens must NOT leak into portable revision contracts.
- `UNKNOWN_OUTCOME` must NEVER trigger blind retry; it mandates provider reconciliation.
- PostgreSQL lifecycle evidence survives restart (`pyingestkit_v2_publication_operation`, `pyingestkit_v2_publication_event`, `pyingestkit_v2_version_hold`).
- The durable publication-intent and lifecycle-event codec is frozen at `schema_version = 1`.

### Invariant 3: Garbage Collection & Rollback Guarantees
- Current, held, unresolved, and unverified versions are strictly protected from garbage collection.
- Stale garbage-collection plans MUST fail closed.
- Governed rollback publishes a new CAS revision referencing an existing immutable `DatasetVersion`; it NEVER mutates or deletes historical bytes.

### Invariant 4: Hexagonal Boundary Isolation
- Domain (`src/pyingestkit/domain/`) and Ports (`src/pyingestkit/ports/`) MUST NOT import physical drivers (`psycopg`, `boto3`, `requests`, `httpx`).
- Physical connectors live strictly in `src/pyingestkit/adapters/` and are isolated as optional extras (`postgres`, `s3`, `http`).

### Invariant 5: Contract Fixtures Immutability
- Files in `tests/contract/fixtures/` (`governance_v2_1_stable.json`, `stable_release_v2.json`, etc.) are auditable evidence.
- Agents MUST NEVER alter contract fixtures to make a failing test pass. A mismatch indicates an implementation regression to be fixed in the source code.

---

## 4. Directory Layout

```text
pyingestkit/
├── docs/                       # Architecture specs, RFCs, release notes, plans, and analyses
│   ├── analyses/               # Analytical benchmarks and investigations
│   ├── build/plans/            # Operational implementation plans
│   ├── releases/               # Immutable release qualification and evidence
│   └── rfc/                    # Requests for Comments (RFC-001)
├── src/pyingestkit/            # Core framework package source
│   ├── adapters/               # Physical connectors (filesystem, memory, postgres, s3, http)
│   ├── domain/                 # Pure domain models (governance, acquisition, datasets, runtime)
│   ├── governance/             # Retention, GC, Rollback, Ledger codecs
│   ├── ports/                  # Protocol boundaries and abstract interfaces
│   ├── serialization/          # Portable version-1 envelope codecs
│   └── _version.py             # Package version authority (__version__ = "2.1.0")
├── tests/
│   ├── architecture/           # Automated hexagonal and boundary constraint tests
│   ├── conformance/            # Provider and connector contract conformance suites
│   ├── contract/               # Public API checks and frozen JSON fixture contracts
│   │   └── fixtures/           # Auditable immutable fixture contracts
│   ├── integration/            # Multi-provider, PostgreSQL, S3, CAS, and crash recovery tests
│   └── unit/                   # Fast, isolated unit test suites
├── scripts/                    # Milestone and compatibility check scripts
└── Makefile                    # Standard build and quality execution targets
```

---

## 5. Quality & Verification Gates

Agents must verify all changes using the standard Makefile commands:
- `make architecture-v2` : Verify hexagonal boundaries and contract imports
- `make contract-v2`     : Verify public API signatures and fixture compliance
- `make v2-core`         : Run unit, conformance, and contract tests
- `make check-v2`        : Full test matrix + compilation check
- `make quality`         : Ruff lint, format check, and strict Mypy
- `make security`        : Bandit static analysis and pip-audit
- `make verify`          : Global gate (check-v2 + quality + security + build)
