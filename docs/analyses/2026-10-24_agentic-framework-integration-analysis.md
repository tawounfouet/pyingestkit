# Analyse de l'Intégration de l'Agentique dans les Frameworks : PyIngestKit vs PyTransformKit & PyWorkflowKit

- **Date :** 24 Octobre 2026  
- **Auteur :** Antigravity / Pair Programming  
- **Contexte :** Benchmark des pratiques d'ingénierie agentique (*AI-Assisted SDLC*) et mise à niveau de [`PyIngestKit`](../../README.md).  
- **Références amont :**  
  - [`pytransformkit/AGENTS.md`](../../../pytransformkit/AGENTS.md) & [`pytransformkit/CLAUDE.md`](../../../pytransformkit/CLAUDE.md)  
  - [`pyworkflowkit/AGENTS.md`](../../../pyworkflowkit/AGENTS.md) & [`pyworkflowkit/CLAUDE.md`](../../../pyworkflowkit/CLAUDE.md)  
  - Workspace root [`AGENTS.md`](../../../../AGENTS.md)

---

## 1. Contexte & Problématique

Dans les architectures modernes développées en pair-programming avec des agents IA (Antigravity/Gemini, Claude Code, OpenCode, Cursor), la fiabilité du code produit dépend directement des **instructions de cadrage contextuel** fournies à l'agent au niveau du repository.

### Le constat dans PyIngestKit
Alors que [`PyTransformKit`](../../../pytransformkit) et [`PyWorkflowKit`](../../../pyworkflowkit) disposent d'un outillage agentique mature et standardisé, **PyIngestKit ne possède actuellement ni `AGENTS.md` ni `CLAUDE.md`** à la racine de son package.

Cette absence expose PyIngestKit à des risques opérationnels critiques :
1. **Régression de périmètre (Scope Creep) :** L'agent réintroduit spontanément des abstractions historiques V1 (`Job`, `Pipeline`, `Step`, `Runner`) dans l'API racine V2, alors que celle-ci est sciemment gelée à 11 symboles.
2. **Violation des invariants RFC-001 :** L'agent contourne les mécanismes Compare-and-Swap (CAS), bypass le ledger PostgreSQL immuable, ou affaiblit les règles de protection du Garbage Collector.
3. **Altération des preuves contractuelles :** Face à un test en échec, un agent non instruit a tendance à modifier les fixtures JSON (`tests/contract/fixtures/`) plutôt que de corriger l'implémentation.
4. **Commandes inefficaces ou destructrices :** Tentatives d'utiliser des outils non configurés ou non isolés au lieu des cibles `Makefile` officielles (`make check-v2`, `make quality`, `make verify`).

---

## 2. Modèle d'Intégration Agentique des Frameworks Frères

Dans `pytransformkit` et `pyworkflowkit`, l'intégration agentique repose sur un modèle hiérarchique à deux niveaux, complété par une chaîne d'autorité stricte :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| CASCADE D'AUTORITÉ DU FRAMEWORK AGENTIQUE                                                        |
|                                                                                                   |
|  [ Niveau 0 : Vérité Absolue & Preuves Immuables ]                                                |
|  Spécifications RFC / Contrats JSON de fixtures / Suites de tests d'architecture                  |
|                                      │                                                            |
|                                      ▼                                                            |
|  [ Niveau 1 : Instructions Canoniques du Repository ]                                            |
|  AGENTS.md (Agnostique : Architecture DDD, Invariants non-négociables, Frontières)                |
|                                      │                                                            |
|                                      ▼                                                            |
|  [ Niveau 2 : Surcouche Opérateur / Outil Spécifique ]                                           |
|  CLAUDE.md / Configurations IDE (Workflow de session, checklist pre-flight, commandes)            |
|                                      │                                                            |
|                                      ▼                                                            |
|  [ Niveau 3 : Hypothèses & Suggestions de l'Agent IA ] (Toujours subordonnées aux niveaux 0-2)   |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

### Rôle comparé des fichiers `AGENTS.md` vs `CLAUDE.md`

| Caractéristique | `AGENTS.md` (Fondation universelle) | `CLAUDE.md` (Surcouche opérationnelle) |
| :--- | :--- | :--- |
| **Cible** | Tous agents IA (Gemini, Claude, OpenCode, Cursor) et humains | Claude Code / Antigravity / Assistants de session interactive |
| **Périmètre** | Identité produit, invariants métier, architecture hexagonale, modèle de données | Checklist de démarrage, hygiène de commit, commandes CLI concrètes |
| **Nature des règles** | Invariants permanents, règles d'autorité, contrats de frontières | Procédure opérationnelle pas-à-pas (*pre-flight inspection*) |
| **Dépendance** | Indépendant et autonome | Référence obligatoirement `AGENTS.md` en amont |

---

## 3. Matrice Comparative de l'Agentique

| Pratique Agentique | PyIngestKit (Actuel) | PyTransformKit | PyWorkflowKit |
| :--- | :--- | :--- | :--- |
| **Fichier `AGENTS.md` racine** | ❌ Absent | ✅ Présent (639 lignes) | ✅ Présent (161 lignes) |
| **Fichier `CLAUDE.md` racine** | ❌ Absent | ✅ Présent (478 lignes) | ✅ Présent (124 lignes) |
| **Identité de baseline explicite** | Dispersée dans docs | ✅ Section dédiée (1.2.0 stable) | ✅ Section dédiée (2.1.0 tag / 2.1.1 target) |
| **Invariants d'architecture négatifs** | Aucun | ✅ "Domain MUST NOT depend on pandas/polars..." | ✅ "Core is zero-dependency, deferred otel..." |
| **Protection des fixtures de contrat** | Non documentée pour l'agent | ✅ Règle explicite d'interdiction de réécriture | ✅ Règle explicite de préservation des fixtures |
| **Checklist Pre-flight de session** | Aucune | ✅ Protocole strict en 7 étapes | ✅ Protocole strict en 7 étapes |
| **Cartographie des suites isolées** | Floue pour l'agent | ✅ Détail des suites engine/schema | ✅ Détail des suites standalone `integrations/` |
| **Commandes de validation outillées** | Makefile existant mais non imposé | ✅ Commandes de qualité standardisées | ✅ Commandes typées avec `uv run` |

---

## 4. Les Invariants Clés à Formaliser pour PyIngestKit

En s'inspirant de `pyworkflowkit` et `pytransformkit`, l'intégration agentique de PyIngestKit doit verrouiller **quatre piliers fondamentaux** :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| LES 4 PILIERS DE L'AGENTIQUE DANS PYINGESTKIT                                                     |
|                                                                                                   |
|  1. Frozen 2.x Public Root        2. RFC-001 Governance LifeCycle                                 |
|  - Exactement 11 symboles         - CAS (Compare-and-Swap) obligatoire                            |
|  - IngestionRuntime.run(...)       - Pas d'écriture aveugle ou d'écrasement                        |
|  - Pas d'alias V1 (Job/Pipeline)  - Dual-ledger durable (PostgreSQL / In-Memory)                  |
|  - Source -> RAW -> Version       - Protection GC des holds et des versions actives               |
|                                                                                                   |
|  3. Hexagonal Boundary Isolation  4. Contract Fixtures Immutability                               |
|  - Domain isolé de toute I/O      - Fixtures dans tests/contract/fixtures/ = Preuves              |
|  - Providers dans adapters/       - Interdiction absolue pour un agent d'éditer un JSON           |
|  - Extras optionnels isolés        de contrat pour masquer une régression                         |
|    (postgres, s3, http)           - Schéma de persistance PostgreSQL gelé (v1)                    |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

### Pilier 1 : Gel absolu du Root Public V2
L'agent doit savoir dès sa première lecture que l'API racine est gelée :
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
Toute tentative d'ajouter des classes ou des fonctions à cette liste sans un nouveau RFC et une spécification formelle est **interdite**.

### Pilier 2 : Invariants de Gouvernance RFC-001
- La publication d'un dataset est toujours **conditionnelle** (CAS) : un writer ne peut écraser silencieusement l'état sans fournir la révision attendue (`expected_revision`).
- Les résolutions incertaines (`UNKNOWN_OUTCOME`) ne doivent **jamais** provoquer de retry aveugle sans réconciliation préalable auprès de la vérité du provider.
- Le Garbage Collection (`FileDatasetVersionGarbageCollector`, `S3DatasetVersionGarbageCollector`) échoue en mode fermé (*fail-closed*) si le plan de rétention est périmé.
- Le rollback est gouverné : il publie une nouvelle révision pointant sur les octets immuables d'une version passée, sans jamais altérer l'historique physique.

### Pilier 3 : Isolation Hexagonale & Extras Optionnels
- Le cœur `domain/` et `ports/` ne doit **jamais** dépendre de `psycopg`, `boto3`, ou de connecteurs physiques.
- Les dépendances de connecteurs (`postgres`, `s3`, `http`) doivent rester des extras optionnels avec isolation stricte à l'installation.

### Pilier 4 : Immutabilité des Preuves Contractuelles
- Les fichiers sous `tests/contract/fixtures/` (`governance_v2_1_stable.json`, `stable_release_v2.json`, etc.) représentent la vérité contractuelle.
- Face à un test rouge, l'agent doit corriger son code, jamais la fixture.

---

## 5. Protocole de Session Recommandé pour l'Agent (Pre-Flight)

Pour éviter les régressions, tout agent intervenant sur PyIngestKit doit exécuter le cycle suivant :

```text
  [ Début de session ]
           │
           ▼
  1. Lire AGENTS.md et CLAUDE.md
           │
           ▼
  2. Inspecter la branche Git et la version (git status, pyproject.toml, _version.py)
           │
           ▼
  3. Identifier le document de cadrage (Plan dans docs/build/plans/ ou RFC dans docs/rfc/)
           │
           ▼
  4. Inspecter les tests existants et les fixtures associées
           │
           ▼
  5. Implémenter le changement par incréments minimaux cohérents
           │
           ▼
  6. Exécuter la validation locale ciblée :
     pytest -q tests/unit/v2/test_<composant>.py
           │
           ▼
  7. Exécuter la barrière globale de qualité :
     make check-v2 && make quality
           │
           ▼
  [ Fin de session propre ]
```

---

## 6. Plan d'Action pour Déployer l'Agentique dans PyIngestKit

| Étape | Livrable | Objectif |
| :--- | :--- | :--- |
| **Phase 1** | Création de `AGENTS.md` à la racine de PyIngestKit | Définir l'autorité, les invariants d'architecture V2, les frontières RFC-001 et les règles de préservation |
| **Phase 2** | Création de `CLAUDE.md` à la racine de PyIngestKit | Définir la surcouche opérationnelle (checklist pre-flight, commandes `make`, conventions de session) |
| **Phase 3** | Alignement du `.github/pull_request_template.md` | Lier la checklist de PR aux invariants formalisés dans `AGENTS.md` |
| **Phase 4** | Intégration dans le cycle CI | Ajouter un test d'architecture vérifiant que les agents ne cassent pas les frontières hexagonales |
