# Plan d'Implémentation : Intégration de l'Agentique & Instructions Repository (AGENTS.md & CLAUDE.md)

- **Projet** : PyIngestKit
- **Statut** : Prêt pour implémentation
- **Date** : 24 Octobre 2026
- **Auteur** : Antigravity / Pair Programming
- **Document source** : [`../../analyses/2026-10-24_agentic-framework-integration-analysis.md`](../../analyses/2026-10-24_agentic-framework-integration-analysis.md)
- **Références amont** : [`../../../pytransformkit/AGENTS.md`](../../../pytransformkit/AGENTS.md) & [`../../../pyworkflowkit/AGENTS.md`](../../../pyworkflowkit/AGENTS.md)
- **Branche cible** : `feat/agentic-governance-and-instructions`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation opérationnel a pour objectif d'aligner **PyIngestKit** sur les meilleures pratiques de développement assisté par agents IA (*Agentic SDLC*) établies dans le monorepo, en créant les fichiers d'instructions canoniques à la racine du package :

1. **Création de [`AGENTS.md`](../../../AGENTS.md)** : Fichier canonique agnostique définissant l'identité du projet, l'ordre d'autorité des spécifications, les invariants non-négociables d'architecture (V2 root, RFC-001 CAS, ledgers durables, rollback, GC), et l'interdiction formelle d'altérer les fixtures contractuelles.
2. **Création de [`CLAUDE.md`](../../../CLAUDE.md)** : Surcouche opérationnelle fine pour les sessions de codage interactives (Claude Code, Antigravity, OpenCode), prescrivant une checklist pré-vol (*pre-flight*) rigoureuse et le catalogue exact des commandes `Makefile` de qualité.
3. **Verrouillage de la gouvernance Git** : Liaison directe entre les exigences d'architecture d'`AGENTS.md` et le modèle de revue de code [`.github/pull_request_template.md`](../../../.github/pull_request_template.md).
4. **Zéro régression architecturale** : Prévention active des hallucinations courantes (réintroduction du modèle V1 `Job/Pipeline`, imports illégaux de connecteurs physiques dans le domaine, contournement du Compare-and-Swap).

---

## 2. Diagramme d'Architecture de la Gouvernance Agentique

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| CADRE DE DÉCISION AGENTIQUE POUR PYINGESTKIT                                                      |
|                                                                                                   |
|  [ Événement : Prompt Utilisateur / Session IA ]                                                  |
|                       │                                                                           |
|                       ▼                                                                           |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 1 : Lecture Obligatoire des Instructions Canoniques                                   |  |
|  | - Ordre d'autorité : Spécifications RFC > Fixtures JSON > Tests > AGENTS.md > CLAUDE.md     |  |
|  | - Identification de la Baseline : PyIngestKit 2.1.0 Stable (LOT-30)                         |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                       │                                                                           |
|                       ▼                                                                           |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 2 : Vérification des Garde-Fous Invariants (Negative Guardrails)                       |  |
|  |                                                                                             |  |
|  |  [ X ] Ne JAMAIS élargir l'API racine (11 symboles gelés, IngestionRuntime.run)             |  |
|  |  [ X ] Ne JAMAIS importer V1 Job/Pipeline/Runner dans le root V2                           |  |
|  |  [ X ] Ne JAMAIS publier sans CAS (Compare-and-Swap avec expected_revision)                |  |
|  |  [ X ] Ne JAMAIS modifier les fixtures JSON dans tests/contract/fixtures/                  |  |
|  |  [ X ] Ne JAMAIS introduire de dépendance physique (psycopg, boto3) dans domain/          |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                       │                                                                           |
|                       ▼                                                                           |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 3 : Exécution Incrémentale & Barrières de Qualité                                      |  |
|  | - Tests unitaires ciblés : pytest tests/unit/v2/...                                         |  |
|  | - Barrière d'architecture : make architecture-v2                                            |  |
|  | - Barrière de qualité globale : make check-v2 && make quality                                |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                       │                                                                           |
|                       ▼                                                                           |
|  [ Code Conforme, Prouvé et Livrable via PR Template ]                                            |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
pyingestkit/
├── AGENTS.md                           # [CRÉATION] Instructions canoniques universelles pour agents IA
├── CLAUDE.md                           # [CRÉATION] Surcouche opérationnelle et checklist de session
└── .github/
    └── pull_request_template.md        # [SYNCHRONISATION] Alignement de la checklist sur les invariants
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Spécification & Contenu de `AGENTS.md`
**Fichier à créer :** [`AGENTS.md`](../../../AGENTS.md) (à la racine de `pyingestkit`)

```markdown
# AGENTS.md

# PyIngestKit — Repository Instructions for Coding Agents

This file defines the canonical repository-level instructions for AI coding agents and automated contributors working on PyIngestKit.
It applies to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory.

Human-maintained specifications, public contracts, tests, and release evidence remain authoritative over agent assumptions.

## 1. Repository identity

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

## 3. Non-negotiable Architecture Invariants

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
- The canonical execution method is `IngestionRuntime.run(...)`.
- DO NOT reintroduce or alias V1 `Job`, `Pipeline`, `Step`, or `Runner` into the 2.x root.
- Governance APIs remain additive under qualified namespaces (`pyingestkit.governance.*`).

### Invariant 2: RFC-001 Lifecycle Governance & CAS
- Publication is ALWAYS compare-and-swap (CAS), never blind overwrite.
- Exactly one writer succeeds for the same expected revision.
- Publication revisions prevent ABA; provider ETags must NOT leak into portable revision contracts.
- `UNKNOWN_OUTCOME` must NEVER trigger blind retry; it mandates provider reconciliation.
- PostgreSQL lifecycle evidence survives restart (`pyingestkit_v2_publication_operation`, `pyingestkit_v2_publication_event`, `pyingestkit_v2_version_hold`).

### Invariant 3: Garbage Collection & Rollback Guarantees
- Current, held, unresolved, and unverified versions are protected from GC.
- Stale GC plans MUST fail closed.
- Governed rollback publishes a new CAS revision referencing an existing immutable `DatasetVersion`; it NEVER mutates or deletes historical bytes.

### Invariant 4: Hexagonal Boundary Isolation
- Domain (`src/pyingestkit/domain/`) and Ports (`src/pyingestkit/ports/`) MUST NOT import physical drivers (`psycopg`, `boto3`, `requests`).
- Physical connectors live strictly in `src/pyingestkit/adapters/` and are isolated as optional extras (`postgres`, `s3`, `http`).

### Invariant 5: Contract Fixtures Immutability
- Files in `tests/contract/fixtures/` (`governance_v2_1_stable.json`, `stable_release_v2.json`, etc.) are auditable evidence.
- Agents MUST NEVER alter contract fixtures to make a failing test pass.

## 4. Quality & Verification Gates

Agents must verify all changes using the standard Makefile commands:
- `make architecture-v2` : Architecture boundary verification
- `make contract-v2`     : Public API and contract compliance
- `make v2-core`         : Unit, conformance, and contract tests
- `make check-v2`        : Complete V2 test matrix and compilation
- `make quality`         : Ruff lint, format check, and Mypy
- `make security`        : Bandit and pip-audit checks
- `make verify`          : Full verification (check-v2 + quality + security + build)
```

---

### Phase 2 — Spécification & Contenu de `CLAUDE.md`
**Fichier à créer :** [`CLAUDE.md`](../../../CLAUDE.md) (à la racine de `pyingestkit`)

```markdown
# CLAUDE.md

# PyIngestKit — Claude Code & Interactive Agent Instructions

This file contains operational instructions for Claude Code, Antigravity, and interactive coding sessions.
It is intentionally a thin overlay. The canonical repository-wide instructions live in:

```text
AGENTS.md
```

Agents MUST read and follow `AGENTS.md` before making changes.

## 1. First action in every coding session (Pre-Flight Protocol)

Before editing code:
```text
1. Read AGENTS.md.
2. Check git status and current branch (git status -sb).
3. Confirm version in src/pyingestkit/_version.py and pyproject.toml.
4. Inspect the relevant RFC, release note, or implementation plan.
5. Inspect adjacent test suites and contract fixtures.
6. Plan changes strictly respecting the frozen 2.x root and RFC-001 invariants.
```

The live repository is the source of truth. Never assume state from memory or stale notes.

## 2. Preferred Test & Development Cycle

```text
inspect
  → implement small, coherent change
  → run targeted test: pytest -q tests/unit/v2/test_<target>.py
  → fix and refine
  → run architecture check: make architecture-v2
  → run full baseline: make check-v2
  → check style and types: make quality
```

Do not defer all verification to the end of the session.

## 3. Standard Commands Cheatsheet

```bash
# Targeted testing
pytest tests/unit/v2/test_<name>.py -v
pytest tests/architecture/ -v
pytest tests/contract/public_api/ -v

# Global quality checks
make quality        # Ruff check + format + Mypy
make check-v2       # Architecture + Conformance + Unit + Integration
make verify         # check-v2 + quality + security + build

# Documentation
make docs-build     # mkdocs build --strict
make docs-serve     # mkdocs serve
```

## 4. Prohibited Actions for Agents

- DO NOT add new exports to `pyingestkit/__init__.py`.
- DO NOT reintroduce `Job`, `Pipeline`, or `Step` in V2 code.
- DO NOT edit JSON files under `tests/contract/fixtures/` to fix test failures.
- DO NOT bypass Compare-and-Swap in conditional publishers.
- DO NOT add top-level imports of `psycopg` or `boto3` in core or domain modules.
```

---

### Phase 3 — Harmonisation du Template de Pull Request
**Fichier à synchroniser :** [`.github/pull_request_template.md`](../../../.github/pull_request_template.md)

Le template de PR fait référence directe aux règles de `AGENTS.md` pour garantir que tout contributeur ou agent valide les mêmes invariants avant merge.

---

## 5. Matrice de Risques & Contrôles

| Risque identifié | Probabilité | Impact | Mesure de mitigation |
| :--- | :--- | :--- | :--- |
| **L'agent ignore `AGENTS.md`** | Faible | Élevé | Règle de rappel explicite dans `CLAUDE.md` et en-tête des sessions |
| **Régression silencieuse des 11 symboles racine** | Faible | Critique | Test automatisé `tests/contract/public_api/test_v2_governance.py` vérifié par `make check-v2` |
| **Modification involontaire d'une fixture de contrat** | Faible | Élevé | Invariant 5 dans `AGENTS.md` et interdiction explicite dans `CLAUDE.md` |
| **Rupture des imports optionnels (`postgres`, `s3`)** | Faible | Élevé | Test `clean wheel install and optional-provider isolation` validé par la CI |

---

## 6. Critères d'Acceptation & Validation

- [ ] [`AGENTS.md`](../../../AGENTS.md) est présent à la racine de `pyingestkit` et documente les invariants 2.1.0 et RFC-001.
- [ ] [`CLAUDE.md`](../../../CLAUDE.md) est présent à la racine de `pyingestkit` avec la checklist pre-flight et les commandes `Makefile`.
- [ ] Tous les liens internes des documents sont strictement relatifs.
- [ ] La commande `make architecture-v2` confirme l'étanchéité des frontières hexagonales.
- [ ] La commande `make quality` (Ruff + Mypy) s'exécute sans erreur sur l'ensemble du projet.
- [ ] La suite complète `make verify` valide le code et les distributions.
