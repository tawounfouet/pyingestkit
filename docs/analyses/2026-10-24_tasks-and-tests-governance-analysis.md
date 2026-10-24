# Analyse de Gouvernance des Dossiers `tasks` et `tests` : Cycle de Delivery dans `docs/build` vs Racine du Package

- **Date :** 24 Octobre 2026  
- **Auteur :** Antigravity / Pair Programming  
- **Contexte :** Structuration du cycle d'ingénierie logicielle (*SDLC*), gouvernance des tâches opérationnelles (*tasks*) et clarification architecturale sur l'emplacement des tests (*tests*) pour [`PyIngestKit`](../../README.md).  
- **Références amont :**  
  - Analyse d'hygiène de la racine : [`docs/analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md`](./2026-10-24_backlog-governance-and-root-hygiene-analysis.md)  
  - Plans d'implémentation : [`docs/build/plans/`](../build/plans/)  
  - Stratégies de test des frères :  
    - [`pytransformkit/docs/specifications/PYKIT_ECOSYSTEM_V2_ARCHITECTURE_CONFORMANCE_AND_TEST_STRATEGY.md`](../../../pytransformkit/docs/specifications/PYKIT_ECOSYSTEM_V2_ARCHITECTURE_CONFORMANCE_AND_TEST_STRATEGY.md)  
    - [`pyworkflowkit/docs/architecture/v2-lot28-test-matrix-and-implementation-roadmap.md`](../../../pyworkflowkit/docs/architecture/v2-lot28-test-matrix-and-implementation-roadmap.md)  
  - Instructions agentiques : [`AGENTS.md`](../../AGENTS.md) & [`CLAUDE.md`](../../CLAUDE.md)

---

## 1. Contexte & Problématique

Dans la continuité de la rationalisation de l'arborescence et de l'assainissement de la racine de `pyingestkit`, deux questions clés d'organisation du travail et de gouvernance se posent :

1. **Le dossier `tasks` :** Est-il pertinent d'introduire un dossier `tasks` ? Doit-il résider directement dans `docs/build/` ou ailleurs dans le repository ? Quel est son rôle exact par rapport à `docs/build/backlog/` et `docs/build/plans/` ?
2. **Le dossier `tests` :** Faut-il également intégrer ou déplacer un dossier `tests` dans `docs/build/` ou ailleurs ? Quelle est la frontière stricte entre le **code de test exécutable** (Pytest) et les **artefacts de qualification/rapports de test** (Markdown, matrices, PV de recette) ?

Cette analyse formule les réponses architecturales formelles en s'appuyant sur les standards de l'écosystème Python (PyPA, PEP 517/621) et les pratiques observées dans [`pytransformkit`](../../../pytransformkit) et [`pyworkflowkit`](../../../pyworkflowkit).

---

## 2. Analyse du Dossier `tasks` : Pertinence et Emplacement

### A. Pertinence d'un Dossier `tasks`

Dans un modèle d'ingénierie orienté spécifications (*spec-driven development*) et assisté par des agents IA (Antigravity, Claude Code, OpenCode), il est contre-productif de confondre les niveaux de granularité.

On distingue **trois niveaux d'abstraction et d'horizon temporel** :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| PYRAMIDE DES NIVEAUX DE PLANIFICATION ET D'EXÉCUTION TECHNIQUE                                    |
|                                                                                                   |
|                        ▲                                                                          |
|                       / \                                                                         |
|                      /   \       1. MACRO : VISION & PRODUIT (docs/roadmap/ & ROADMAP.md)          |
|                     /     \         - Epics, jalons SemVer (v2.2.0, v3.0.0), arbitrages           |
|                    /───────\                                                                      |
|                   /         \    2. MÉSO : PLANS DIRECTEURS (docs/build/plans/)                   |
|                  /           \      - Architecture par LOT, matrice d'impact, phases globales     |
|                 /─────────────\                                                                   |
|                /               \ 3. MICRO : TÂCHES OPÉRATIONNELLES (docs/build/tasks/)            |
|               /                 \   - Découpage WBS unitaire, checklists de session agentique     |
|              ─────────────────────                                                                |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

1. **Le Backlog (`docs/build/backlog/`) :** Répond à la question *« Quoi faire ? »*. Il contient les besoins bruts, idées de fonctionnalités, retours utilisateurs ou dettes techniques non encore arbitrés.
2. **Les Plans (`docs/build/plans/`) :** Répondent à la question *« Comment l'architecturer et le cadencer ? »*. Ce sont les plans directeurs multi-phases (ex: le plan CLI en 5 phases ou le plan Release en 4 étapes).
3. **Les Tâches (`docs/build/tasks/`) :** Répondent à la question *« Quelle action concrète exécuter maintenant ? »*. C'est le découpage WBS (*Work Breakdown Structure*) en fiches atomiques pour une session de développement donnée.

### B. Pourquoi l'Emplacement `docs/build/tasks/` est Optimal

#### 1. Synergie avec le sous-arbre `docs/build/`
Le répertoire [`docs/build/`](../build/) a pour vocation exclusive de centraliser le **cycle de vie actif du delivery logiciel**.
Y héberger `tasks/` aux côtés de `backlog/` et `plans/` offre une arborescence parfaitement symétrique :
- `docs/build/backlog/` ➔ Besoins bruts qualifiés
- `docs/build/plans/` ➔ Plans directeurs par LOT
- `docs/build/tasks/` ➔ Tâches unitaires d'exécution de session
- `docs/build/reports/` ➔ Rapports d'exécution et métriques
- `docs/build/reviews/` ➔ Revues formelles et signatures

#### 2. Optimisation de la Fenêtre de Contexte des Agents IA
Dans les environnements modernes de pair-programming agentique :
- Un plan d'implémentation complet fait entre 300 et 600 lignes (architecture, tableaux comparatifs, matrices de risques, commandes de rollback).
- Lorsqu'un agent IA intervient sur une sous-partie précise (ex: implémenter uniquement `src/pyingestkit/cli/exit_codes.py`), lui fournir l'intégralité du plan gaspille des tokens de contexte et augmente le risque d'hallucination ou de dérive.
- Avoir une fiche de tâche unitaire dans `docs/build/tasks/` (ex: `TASK-LOT31-02_exit-codes.md`, 50 lignes ciblées avec entrées, sorties et tests associés) permet d'alimenter l'agent avec un contexte chirurgical à haute densité informationnelle.

### C. Gabarit Standard d'une Fiche de Tâche (`docs/build/tasks/`)

Toute fiche de tâche respecte une nomenclature conventionnelle :  
`docs/build/tasks/TASK-<LOT>-<NUMERO>_<intitule-court>.md`

```markdown
# TASK-LOT31-01 : Implémentation du Bootstrap CLI

- **Statut :** TODO | IN_PROGRESS | DONE
- **Plan Parent :** [docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Agent / Développeur :** Antigravity / AWF
- **Date :** 2026-10-24

## 1. Objectif Unitaire
Créer le module de bootstrap stdlib `src/pyingestkit/cli/bootstrap.py` détectant `typer` et `rich`.

## 2. Fichiers Cibles
- `src/pyingestkit/cli/bootstrap.py`
- `tests/unit/cli/test_bootstrap.py`

## 3. Checklist d'Exécution
- [ ] Détecter la présence des dépendances optionnelles via `importlib.util.find_spec`.
- [ ] Formater le message d'erreur d'installation (`pip install "pyingestkit[cli]"`).
- [ ] Intercepter proprement `BrokenPipeError` et `KeyboardInterrupt`.
- [ ] Écrire le test unitaire d'isolation.

## 4. Commande de Validation
```bash
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/test_bootstrap.py -v
```
```

---

## 3. Analyse du Dossier `tests` : Clarification Architecturale Fondamentale

La question posée est :
> *"Idem pour le dossier `tests` : faut-il le mettre directement dans build ou ailleurs ?"*

La réponse impose de dissocier rigoureusement **deux réalités techniques radicalement distinctes** :
1. Le **Code Source Exécutable de Test** (Python / Pytest).
2. La **Documentation, Stratégie et Rapports de Qualification de Test** (Markdown / JSON).

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| LA DICHOTOMIE FONDAMENTALE DU CONCEPT DE « TESTS »                                                |
|                                                                                                   |
|  ┌──────────────────────────────────────────────┐  ┌────────────────────────────────────────────┐ |
|  │  1. CODE DE TEST PYTHON EXÉCUTABLE           │  │  2. DOCUMENTATION & RAPPORTS DE QUALIF.    │ |
|  │                                              │  │                                            │ |
|  │  tests/ (À LA RACINE — INVIOLABLE)           │  │  docs/build/reports/tests/ (DANS BUILD)    │ |
|  │  ├── unit/                                   │  │  ├── PV d'exécution (test execution logs)  │ |
|  │  ├── integration/                            │  │  ├── Rapports de couverture HTML/JSON      │ |
|  │  ├── contract/                               │  │  ├── Preuves de non-régression V2.1.0      │ |
|  │  └── architecture/                           │  │  └── Matrices d'acceptation par LOT        │ |
|  │                                              │  │                                            │ |
|  │  • Exécuté par Pytest                        │  │  • Lu par les humains et auditeurs         │ |
|  │  • Requis par PEP 517 / Hatchling            │  │  • Artefact de gouvernance documentaire    │ |
|  │  • Indexé par les IDEs et la CI              │  │  • Preuve de passage de jalon              │ |
|  └──────────────────────────────────────────────┘  └────────────────────────────────────────────┘ |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

### A. Le Code de Test Exécutable : Pourquoi `tests/` DOIT Rester à la Racine

Déplacer le dossier de code de test `tests/` dans `build/` ou dans `docs/` serait une **erreur critique d'architecture** pour les raisons suivantes :

1. **Standard Canonique Python (PEP 517 / PEP 621 / PyPA) :**
   Dans l'écosystème Python moderne, tous les outils de build (`hatchling`, `flit`, `poetry`, `setuptools`) et d'exécution de tests (`pytest`, `tox`, `coverage`) considèrent par convention que le code applicatif vit dans `./src/` et le code de test automatisé dans `./tests/` à la racine.
2. **Configuration Outillée Existante :**
   Dans [`pyproject.toml`](../../pyproject.toml) :
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   ```
   Toutes les cibles du [`Makefile`](../../Makefile) (`make test-v2`, `make contract-v2`, `make architecture-v2`, `make quality`) reposent sur cette racine `./tests/`.
3. **Alignement avec les Packages Frères :**
   - [`pytransformkit`](../../../pytransformkit) possède son dossier de tests à la racine : `pytransformkit/tests/`
   - [`pyworkflowkit`](../../../pyworkflowkit) possède son dossier de tests à la racine : `pyworkflowkit/tests/`
   Aucun projet de l'écosystème ne déplace ses tests exécutables dans `build/` ou `docs/`.
4. **Intégration CI/CD et IDEs :**
   Les workflows GitHub Actions (`.github/workflows/ci.yml`) et les analyseurs de workspace des IDEs (Cursor, VS Code Test Explorer, PyCharm) s'appuient sur la détection native de `./tests/`.

> **Conclusion Impérative :** Le dossier de code `./tests/` est **strictement inviolable et doit demeurer à la racine du repository**.

---

### B. Les Artefacts et Rapports de Test dans `docs/build/`

Si le code reste à la racine, **qu'est-ce qui appartient légitimement à `docs/build/` concernant les tests ?**

Dans `docs/build/`, les tests n'interviennent pas sous forme de code Python, mais sous forme de **livrables de qualification et d'assurance qualité (QA)**.

On distingue deux types de documentation de test :

| Nature du Livrable | Description | Emplacement Recommandé |
| :--- | :--- | :--- |
| **Stratégie de Test Pérenne** | Doctrine globale d'assurance qualité, règles de mock, isolation des couches hexagonales, tolérance zéro régression sur les 11 symboles publics. | [`docs/architecture/`](../architecture/) ou [`docs/reference/`](../reference/) *(Pérenne, ne change pas à chaque build)* |
| **Matrice de Test par LOT** | Tableau des cas de test requis pour valider un lot spécifique (critères d'acceptation, cas limites, tests de régression). | Section dédiée dans [`docs/build/plans/`](../build/plans/) *(Spécifique au chantier)* |
| **Procès-Verbaux & Rapports de Test** | Traces d'exécution horodatées des suites de tests, rapports de couverture de code (Coverage.py), métriques de temps d'exécution, signatures de conformité. | **`docs/build/reports/tests/`** *(Livrable d'exécution du build)* |

#### Pourquoi `docs/build/reports/tests/` plutôt qu'un dossier `docs/build/tests/` ?
Créer un dossier `docs/build/tests/` prêterait à confusion avec le dossier de code `tests/` de la racine.
En revanche, structurer les rapports dans **`docs/build/reports/tests/`** :
- Respecte le principe de factorisation : `docs/build/reports/` est le réceptacle naturel de tous les rapports (rapports de performance, rapports de sécurité, rapports de test).
- Évite la collision sémantique entre le *code de test* (`tests/`) et le *rapport de test* (`reports/tests/`).
- Fournit une localisation claire pour les exports CI (`pytest --junitxml=...`, `coverage html`).

---

## 4. Matrice de Décision Complète

| Élément | Question Posée | Décision d'Architecture | Emplacement Validé | Justification Majeure |
| :--- | :--- | :--- | :--- | :--- |
| **Dossier `tasks`** | *Faut-il le rajouter ?* | **OUI** | **`docs/build/tasks/`** | Permet le découpage WBS unitaire des plans par LOT ; optimise la fenêtre de contexte des agents IA. |
| **Dossier `tests` (Code)** | *Faut-il le mettre dans build ?* | **NON (Inviolable)** | **`tests/` (Racine)** | Standard universel Python (PEP 517/621, Pytest, CI, IDEs). Alignement strict avec `pytransformkit` et `pyworkflowkit`. |
| **Rapports de Test** | *Où stocker les preuves de test ?* | **OUI (Dans build)** | **`docs/build/reports/tests/`** | Évite la confusion sémantique ; s'intègre harmonieusement dans les rapports de build du SDLC. |
| **Stratégie de Test** | *Où formaliser la stratégie ?* | **PÉRENNE** | **`docs/architecture/`** | Documentation vivante de référence, découplée des runs temporaires. |

---

## 5. Architecture Cible Unifiée du Cycle SDLC dans `docs/build/`

L'intégration conjointe de `backlog/`, `plans/`, `tasks/`, `reports/` et `reviews/` forme la structure définitive du sous-arbre [`docs/build/`](../build/) :

```text
pyingestkit/
├── src/                                  <-- Code source du framework hexagonal
├── tests/                                <-- CODE DE TEST AUTOMATISÉ (Strictement à la racine)
│   ├── architecture/                     <-- Conformité hexagonale et contrats 11 symboles
│   ├── contract/                         <-- Fixtures immuables et non-régression V1/V2
│   ├── integration/                      <-- Tests avec bases PostgreSQL et MinIO S3
│   └── unit/                             <-- Tests unitaires isolés ultra-rapides
│
├── docs/
│   ├── analyses/                         <-- Études comparatives et benchmarks
│   ├── architecture/                     <-- Décisions pérennes (RFC, ADR, stratégie de test)
│   │
│   └── build/                            <-- CYCLE COMPLET DE DELIVERY & GOUVERNANCE DU BUILD
│       ├── backlog/                      <-- 1. BESOINS & DETTES (Tickets bruts à cadrer)
│       │   └── README.md
│       │
│       ├── plans/                        <-- 2. PLANS DIRECTEURS (Feuilles de route par LOT)
│       │   ├── 2026-10-24_plan-release-automation-and-supply-chain.md
│       │   ├── 2026-10-24_plan-brand-assets-integration.md
│       │   ├── 2026-10-24_plan-agentic-framework-integration.md
│       │   └── 2026-10-24_plan-cli-architecture-and-pik-standardization.md
│       │
│       ├── tasks/                        <-- 3. TÂCHES OPÉRATIONNELLES WBS (Fiches atomiques de session)
│       │   └── README.md
│       │
│       ├── reports/                      <-- 4. PREUVES D'EXÉCUTION & AUDITS
│       │   ├── tests/                    <-- PV d'exécution, matrices de recette, couverture
│       │   ├── benchmarks/               <-- Métriques de performance I/O et ingestion
│       │   └── security/                 <-- Scans Bandit, pip-audit, SBOM CycloneDX
│       │
│       └── reviews/                      <-- 5. REVUES DE CONFORMITÉ & CLÔTURE
│           └── README.md                 <-- Signatures formelles de livraison de LOT
```

---

## 6. Flux d'Ingénierie Séquentiel (Cycle de Vie d'un Lot)

Ce flux garantit une traçabilité totale sans ambiguïté entre le code et sa gouvernance documentaire :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| FLUX OPÉRATIONNEL DU CYCLE DE VIE D'UN CHANTIER DANS PYINGESTKIT                                  |
|                                                                                                   |
|  [ Étape 1 : Cadrage du Besoin ]                                                                  |
|  Émission d'un besoin brut ou d'une dette dans `docs/build/backlog/`                              |
|                                  │                                                                |
|                                  ▼                                                                |
|  [ Étape 2 : Conception Architecturale ]                                                          |
|  Rédaction de l'analyse dans `docs/analyses/` et du plan directeur dans `docs/build/plans/`       |
|                                  │                                                                |
|                                  ▼                                                                |
|  [ Étape 3 : Découpage Atomique WBS ]                                                             |
|  Génération des fiches unitaires de session dans `docs/build/tasks/`                              |
|                                  │                                                                |
|                                  ▼                                                                |
|  [ Étape 4 : Implémentation & Tests Automatisés ]                                                 |
|  Développement dans `src/` et écriture des suites de tests dans `tests/`                          |
|                                  │                                                                |
|                                  ▼                                                                |
|  [ Étape 5 : Qualification & Preuves ]                                                            |
|  Génération des rapports de validation et couverture dans `docs/build/reports/tests/`             |
|                                  │                                                                |
|                                  ▼                                                                |
|  [ Étape 6 : Revue Formelle & Clôture ]                                                           |
|  Signature de conformité dans `docs/build/reviews/` et archivage de la tâche                      |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 7. Recommandations Finales & Plan d'Action

1. **Création Immédiate :**
   - Créer le dossier **`docs/build/tasks/`** avec son fichier de cadrage [`README.md`](../build/tasks/README.md) définissant le format de ticket WBS.
   - Créer le dossier **`docs/build/reports/tests/`** pour recevoir les prochains procès-verbaux de qualification des suites V2.1.0 et CLI.
2. **Préservation Stricte :**
   - **Garder inviolable `./tests/` à la racine** pour tout le code Python de validation automatisée.
3. **Synergie avec le Nettoyage de la Racine :**
   - Cette architecture s'intègre parfaitement avec le plan d'assainissement de la racine (passage de 38 à 22 entrées), matérialisant un framework de rang industriel à l'état de l'art du monorepo.
