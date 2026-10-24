# Analyse de Gouvernance du Backlog et d'Hygiène de la Racine : PyIngestKit vs PyTransformKit & PyWorkflowKit

- **Date :** 24 Octobre 2026  
- **Auteur :** Antigravity / Pair Programming  
- **Contexte :** Rationalisation de l'arborescence, assainissement de la racine et gouvernance du backlog technique pour [`PyIngestKit`](../../README.md).  
- **Références amont :**  
  - Arborescence racine [`pytransformkit`](../../../pytransformkit) & [`pytransformkit/AGENTS.md`](../../../pytransformkit/AGENTS.md)  
  - Arborescence racine [`pyworkflowkit`](../../../pyworkflowkit), [`pyworkflowkit/ROADMAP.md`](../../../pyworkflowkit/ROADMAP.md) & [`pyworkflowkit/docs/plans/`](../../../pyworkflowkit/docs/plans/)  
  - Plans de livraison PyIngestKit : [`docs/build/plans/`](../build/plans/)  
  - Analyses comparatives : [`docs/analyses/`](./)

---

## 1. Contexte & Problématique

Un repository de framework open-source et enterprise (destiné à être distribué sur PyPI et intégré dans des monorepos de production) doit présenter une **racine épurée, canonique et standardisée**.

### Le Constat Actuel sur PyIngestKit

L'inspection de la racine de `pyingestkit` révèle une surcharge cognitive importante avec **38 entrées** :

```text
pyingestkit (racine actuelle)
├── .DS_Store                             <-- Résidu système macOS (bruit de workspace)
├── .editorconfig
├── .env / .env.example
├── .git / .github / .gitignore
├── .mypy_cache / .pytest_cache / ...     <-- Caches locaux
├── AGENTS.md / CLAUDE.md                 <-- Instructions agentiques (socle V2.1)
├── CHANGELOG.md / CONTRIBUTING.md / ...  <-- Gouvernance standard
├── LICENSE / Makefile / README.md
├── SHA256SUMS-v0.2.0.txt                 <-- Résidu d'intégrité V0.2.0 obsolète à la racine
├── backlog/                              <-- Dossier backlog orphelin / non formalisé
├── dist/
├── docker-compose.staging.yml            <-- Fichier d'infrastructure de test à la racine
├── docs/
├── envs/                                 <-- Dossier de gabarits d'environnement à la racine
├── examples/
├── mkdocs.yml / pyproject.toml
├── pyingest-s3.example.yml               <-- Fichier de configuration applicative loose
├── pyingest.yml                          <-- Fichier de configuration applicative loose
├── pyingest.yml.dev                      <-- Profil dev applicatif loose
├── pyingest.yml.example                  <-- Exemple applicatif loose
├── pyingest.yml.prod                     <-- Profil prod applicatif loose
├── pyingest.yml.stg                      <-- Profil staging applicatif loose
├── scripts/ / src/ / tests/
```

Deux problématiques majeures émergent de cet état :
1. **Pollution de la racine par des configurations applicatives et artefacts de déploiement :** 6 fichiers YAML de configuration, 1 docker-compose et 1 dossier `envs/` sont situés à la racine du framework, donnant au repository une allure de projet d'application finale plutôt que de bibliothèque réutilisable.
2. **Gouvernance du backlog non standardisée :** Absence de convention claire sur l'emplacement du backlog technique, entre la racine (`./backlog`), la documentation générale (`docs/`), les dossiers de cycle de vie (`docs/build/`) et les documents de feuille de route stratégique (`docs/roadmap/`).

---

## 2. Benchmark Comparatif : PyIngestKit vs PyTransformKit & PyWorkflowKit

L'analyse comparative avec les deux bibliothèques sœurs [`pytransformkit`](../../../pytransformkit) et [`pyworkflowkit`](../../../pyworkflowkit) met en lumière des standards d'hygiène stricts :

| Critère d'Arborescence | PyIngestKit (Actuel) | PyTransformKit | PyWorkflowKit | Standard Cible Recommandé |
| :--- | :--- | :--- | :--- | :--- |
| **Nombre total d'entrées racine** | **38** (Encombré) | **25** (Épuré) | **31** (Structuré) | **≤ 24 entrées** |
| **Fichiers YAML applicatifs à la racine** | **6 fichiers** (`pyingest*.yml`) | **0 fichier** | **0 fichier** | **0 fichier** (Logés dans `examples/configs/`) |
| **Fichiers d'infra Docker à la racine** | `docker-compose.staging.yml` | Aucun à la racine | Aucun à la racine | Logé dans `deployment/` |
| **Emplacement du Backlog & Plans** | Éparpillé (`backlog/`, `docs/build/`, `docs/roadmap/`) | `docs/specifications/` | `ROADMAP.md` (macro) + `docs/plans/` (lots) | `docs/build/backlog/` (tech) + `ROADMAP.md` / `docs/roadmap/` (macro) |
| **Résidus de signatures de release** | `SHA256SUMS-v0.2.0.txt` | Aucun à la racine | Aucun à la racine | Archivé dans `docs/releases/` ou GitHub Release |
| **Dossier de templates d'environnement** | `envs/` à la racine | Intégré dans tooling | Aucun à la racine | `deployment/envs/` ou `examples/envs/` |
| **Instructions Agentiques** | `AGENTS.md` + `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` (Aligné ✅) |

### Ce que font les Frameworks Frères

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| STRUCTURE DE RÉFÉRENCE DES FRAMEWORKS FRÈRES (PYTRANSFORMKIT & PYWORKFLOWKIT)                     |
|                                                                                                   |
|  Racine Canonique (Zéro configuration loose) :                                                    |
|  ├── .editorconfig, .gitignore, .env.example                                                      |
|  ├── AGENTS.md, CLAUDE.md, README.md, LICENSE, CHANGELOG.md, SECURITY.md                          |
|  ├── pyproject.toml, Makefile, mkdocs.yml                                                         |
|  ├── src/                <-- Code source du package pur                                           |
|  ├── tests/              <-- Suites unitaire, intégration, contrat, architecture                  |
|  ├── scripts/            <-- Scripts de qualification, tooling CI/CD et release                   |
|  ├── examples/           <-- Cas d'usage réels ET gabarits de configuration (configs/profiles)     |
|  └── docs/               <-- Documentation technique et ingénierie de delivery                    |
|      ├── analyses/       <-- Benchmarks, audits, études d'impact architectural                    |
|      ├── architecture/   <-- RFCs, ADRs, schémas hexagonaux                                       |
|      ├── plans/          <-- Plans d'implémentation opérationnels par lot technique               |
|      └── releases/       <-- Preuves de release, notes de version, matrices de stabilité          |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Analyse de la Gouvernance du Backlog : Emplacement Optimal

La question posée est :
> *"Ne serait-il pas pertinent de tenir un dossier de backlogs dans `docs/` ? Quel est le meilleur endroit : `docs/build/backlog` ou ailleurs ?"*

### A. Pourquoi un dossier `backlog/` à la racine est un Anti-Pattern
1. **Pollution du package source (`sdist`) :** Les outils de build (`hatchling`, `flit`, `setuptools`) risquent d'embarquer des tickets de gestion interne dans les archives distribuées s'ils ne sont pas explicitement exclus.
2. **Confusion de responsabilité :** La racine doit décrire le projet pour l'utilisateur et les outils de packaging (`pyproject.toml`, `README.md`). La gestion opérationnelle des tâches appartient à la documentation d'ingénierie ou au ticketing.
3. **Absence de modèle dans l'écosystème :** Aucun package sérieux (Django, Celery, Pydantic, Polars, ni les siblings `pytransformkit` / `pyworkflowkit`) ne maintient de répertoire `backlog/` à sa racine.

### B. Analyse Comparative des Options dans `docs/`

```text
                              ┌── Option 1: docs/backlog/ (Isolé)
                              │   └── Déconnecté du reste du cycle d'ingénierie
                              │
Emplacement du Backlog ───────┼── Option 2: docs/roadmap/ (Macro)
                              │   └── Parfait pour les RFC et visions pluriannuelles,
                              │       trop lourd pour des items de backlog atomiques
                              │
                              └── Option 3: docs/build/backlog/ (RECOMMANDÉ)
                                  └── Parfaite synergie avec plans, reports et reviews !
```

#### Option 1 : `docs/backlog/`
- **Avantages :** Visibilité immédiate dans la documentation.
- **Inconvénients :** Crée un énième répertoire de premier niveau dans `docs/` (qui en compte déjà 16 !).

#### Option 2 : `docs/roadmap/`
- **Avantages :** Existe déjà (`post-2.0-scope-review.md`, `rfc001-publication-lifecycle-implementation-roadmap.md`).
- **Rôle idéal :** Ce dossier doit rester le réceptacle de la **vision macro-produit** (jalons SemVer 2.2.0, 3.0.0, arbitrage de périmètre). Il n'est pas conçu pour recevoir 50 fiches de user-stories ou tâches de refactoring.

#### Option 3 : `docs/build/backlog/` (La Recommandation Optimale)
Dans `pyingestkit`, le répertoire [`docs/build/`](../build/) regroupe déjà les sous-dossiers :
- `plans/` (Plans d'implémentation opérationnels : CI/CD, CLI, Agentique, Brand Assets)
- `reports/` (Rapports de qualification et d'exécution)
- `reviews/` (Revues formelles de conformité)

### C. Pertinence et Emplacement d'un Dossier `tasks/`

La question se pose légitimement :
> *"Faut-il également rajouter un dossier `tasks` directement dans `docs/build` ou ailleurs ?"*

Dans un cycle de développement assisté par agents IA (Antigravity, Claude Code, OpenCode) et orienté spécifications (*spec-driven engineering*), il existe **trois niveaux de granularité temporelle et d'exécution** :

| Niveau | Granularité | Rôle & Contenu | Emplacement Optimal |
| :--- | :--- | :--- | :--- |
| **Macro / Stratégique** | Mois / Releases | Epics, vision d'ensemble, arbitrage de périmètre, dépréciation V1 | [`docs/roadmap/`](../roadmap/) et [`ROADMAP.md`](../../ROADMAP.md) |
| **Méso / Tactique (Plan)** | Semaines / LOTs | Architecture globale, matrice d'impact, ordonnancement des phases (LOT) | [`docs/build/plans/`](../build/plans/) |
| **Micro / Opérationnel (Tasks)** | Sessions / Jours | Fiches de tâches unitaires, checklists WBS (*Work Breakdown Structure*), tickets atomiques d'exécution | **`docs/build/tasks/`** (Recommandé) |

#### Pourquoi `docs/build/tasks/` est hautement pertinent :
1. **Découplage du Plan Directeur et des Tâches Atomiques :** Un plan d'implémentation (ex: `2026-10-24_plan-cli-architecture-and-pik-standardization.md`) définit l'architecture et les critères de succès. Le dossier `docs/build/tasks/` permet de découper ce plan en fiches d'actions unitaires (ex: `TASK-LOT31-01_bootstrap-module.md`, `TASK-LOT31-02_exit-codes.md`).
2. **Context Window Optimization pour Agents IA :** Un agent opérant sur une tâche spécifique peut charger uniquement sa fiche unitaire dans `tasks/` sans consommer de tokens sur l'intégralité du plan directeur de 500 lignes.
3. **Traçabilité du WBS :** Les tâches passent par des états clairs (`TODO`, `IN_PROGRESS`, `DONE`) et référencent directement leur plan parent.

---

### D. Clarification Fondamentale sur le Dossier `tests/`

La question posée :
> *"Idem pour le dossier `tests` : faut-il le mettre dans build ou ailleurs ?"*

Il est indispensable de distinguer **deux dimensions complètement différentes** pour `tests` :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| DISTINCTION CRITIQUE ENTRE LE CODE DE TEST ET LA DOCUMENTATION DE TEST                            |
|                                                                                                   |
|  1. CODE DE TEST EXÉCUTABLE (Python / Pytest)                                                     |
|     tests/ (À LA RACINE - INVIOLABLE)                                                             |
|     ├── unit/               <-- Tests unitaires rapides sans I/O                                  |
|     ├── integration/        <-- Tests avec dépendances (DB, S3)                                   |
|     ├── contract/           <-- Validation des fixtures JSON et gel d'API                          |
|     └── architecture/       <-- Respect des frontières hexagonales et 11 symboles                 |
|     ==> STANDARD UNIVERSEL PYTHON (PEP 517/621, Pytest, CI/CD, IDEs). NE PAS DÉPLACER !          |
|                                                                                                   |
|  2. DOCUMENTATION & PREUVES DE QUALIFICATION (Markdown / Rapports)                                |
|     docs/build/reports/tests/ OU docs/build/tests/                                                |
|     ├── PV d'exécution et rapports de qualification de release                                    |
|     ├── Rapports de couverture de code (HTML / JSON)                                              |
|     ├── Matrices de tests d'acceptation et critères de recette                                    |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

#### 1. Le dossier de code `tests/` à la racine : NE PAS DÉPLACER
- **Standard de l'industrie :** Dans l'écosystème Python (PyPA, Hatchling, Poetry, Flit), le code de test automatisé doit impérativement résider à la racine dans `./tests/`.
- **Intégration d'outillage :** Les runners (`pytest`), le fichier `pyproject.toml` (`testpaths = ["tests"]`), les configurations de couverture (`.coveragerc`), Mypy, Ruff, les plugins d'IDE (VS Code, Cursor) et les workflows GitHub Actions (`.github/workflows/ci.yml`) s'attendent nativement à trouver `./tests/` à la racine.
- **Alignement avec les frères :** Dans [`pytransformkit/tests`](../../../pytransformkit/tests) et [`pyworkflowkit/tests`](../../../pyworkflowkit/tests), le dossier `tests/` est **strictement maintenu à la racine**. Le déplacer briserait les conventions et l'outillage standard.

#### 2. La documentation et les rapports de test dans `docs/build/` :
- **Matrices de test pérennes & stratégie globale :** Elles appartiennent à la documentation d'architecture : [`docs/architecture/`](../architecture/) (ex: dans `pytransformkit`, `docs/specifications/51_...CLI_TEST_MATRIX_AND_ACCEPTANCE_CRITERIA.md`).
- **Rapports de qualification et procès-verbaux d'exécution :** Ils appartiennent à **`docs/build/reports/tests/`** (ou `docs/build/reports/qa/`). C'est là que l'on consigne les preuves formelles d'exécution des suites (les 367 tests passés de la V2.1.0, les matrices de non-régression, les exports de couverture).

---

### E. Synthèse du Cycle SDLC dans `docs/build/`

Avec l'intégration de `backlog/` et `tasks/`, et la structuration des rapports de tests dans `reports/tests/`, le répertoire [`docs/build/`](../build/) matérialise l'ensemble de la chaîne de valeur du build :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| CYCLE DE GOUVERNANCE DU BUILD COMPLET DANS DOCS/BUILD/                                            |
|                                                                                                   |
|  1. BACKLOG          2. PLANS          3. TASKS          4. REPORTS           5. REVIEWS          |
| ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐ |
| │ docs/build/  │──>│ docs/build/  │─>│ docs/build/  │─>│ docs/build/      │─>│ docs/build/      │ |
| │ backlog/     │   │ plans/       │  │ tasks/       │  │ reports/tests/   │  │ reviews/         │ |
| │              │   │              │  │              │  │                  │  │                  │ |
| │ - Expression │   │ - Plan LOT   │  │ - WBS unit.  │  │ - Preuves tests  │  │ - Conformité RFC │ |
| │ - User Story │   │ - Arch. sync │  │ - Checklist  │  │ - Couverture code│  │ - Signature LOT │ |
| │ - Dette tech │   │ - Test Matrix│  │ - Context agent│ - Audit sécurité  │  │ - Clôture jalon  │ |
| └──────────────┘   └──────────────┘  └──────────────┘  └──────────────────┘  └──────────────────┘ |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 4. Analyse et Stratégie de Nettoyage de la Racine

Pour amener `pyingestkit` au même niveau d'élégance et de rigueur que ses bibliothèques sœurs, la racine doit subir un assainissement ciblé sans casser la rétrocompatibilité des tests.

### A. Fichiers YAML de Configuration Applicative (`pyingest*.yml`)
Actuellement présents à la racine :
- `pyingest.yml`
- `pyingest.yml.dev`
- `pyingest.yml.stg`
- `pyingest.yml.prod`
- `pyingest.yml.example`
- `pyingest-s3.example.yml`

#### Analyse d'impact
Le chargeur de configuration [`src/pyingestkit/config/loader.py`](../../src/pyingestkit/config/loader.py) possède une logique de recherche par défaut :
```python
DEFAULT_CONFIG_FILES = [
    "pyingest.yml",
    ".pyingest.yml",
    "pyingestkit.yml",
]
```
Et lorsque `PYINGEST_ENV` est défini (ex: `PYINGEST_ENV=prod`), il recherche `pyingest.yml.<profile>`.

Cependant :
1. **Les tests de contrat et unitaires** (`test_v1_stability_policy.py`, `test_config.py`) s'exécutent dans des répertoires temporaires isolés (`tmp_path`) et créent leurs propres fichiers de test à la volée. Ils ne dépendent **pas** des fichiers YAML de la racine du repository !
2. Dans un framework distribué, ces fichiers sont des **exemples de référence** ou des configurations de tests d'intégration locaux.
3. Les packages frères [`pytransformkit`](../../../pytransformkit) et [`pyworkflowkit`](../../../pyworkflowkit) ne stockent **aucun fichier de configuration loose à la racine**. Toutes les configurations exemples vivent dans `examples/`.

#### Action Recommandée
- Déplacer l'ensemble de ces profils dans `examples/configs/` :
  ```bash
  mkdir -p examples/configs
  git mv pyingest.yml pyingest.yml.dev pyingest.yml.stg pyingest.yml.prod pyingest.yml.example pyingest-s3.example.yml examples/configs/
  ```
- Pour préserver l'ergonomie des développeurs exécutant `pik` ou `pyingest run` directement à la racine du clone sans `--config`, conserver un lien symbolique ou un gabarit discret `.pyingest.yml.example`.

### B. Infrastructure Docker Staging (`docker-compose.staging.yml`)
- **Fichier :** `docker-compose.staging.yml` (PostgreSQL 16 + MinIO S3).
- **Constat :** Il sert uniquement à lancer la topologie de staging locale pour les tests manuels ou d'intégration.
- **Action Recommandée :** Le déplacer vers `deployment/docker-compose.staging.yml` (ou `examples/deployment/docker-compose.staging.yml`).
- **Mise à jour documentaire :** Mettre à jour [`docs/guides/v1-production-pilot.md`](../guides/v1-production-pilot.md) pour documenter la commande :
  ```bash
  docker compose -f deployment/docker-compose.staging.yml up -d
  ```

### C. Gabarits d'Environnement (`envs/`)
- **Contenu :** `.env.dev.example`, `.env.stg.example`, `.env.prod.example`, `README.md`.
- **Constat :** Ce répertoire est un pendant direct des profils YAML.
- **Action Recommandée :** Le déplacer dans `deployment/envs/` ou `examples/environments/`, permettant de libérer un répertoire de premier niveau à la racine.

### D. Résidus de Release Obsolètes (`SHA256SUMS-v0.2.0.txt`)
- **Fichier :** `SHA256SUMS-v0.2.0.txt`.
- **Constat :** Il s'agit d'une empreinte cryptographique de la version 0.2.0 (datant de plusieurs mois). Les releases modernes (v2.0.0, v2.1.0) publient leurs empreintes dans `docs/releases/` et directement sur les Releases GitHub (`SHA256SUMS-v2.1.0`).
- **Action Recommandée :** Déplacer dans `docs/releases/archive/SHA256SUMS-v0.2.0.txt` ou l'archiver dans l'historique git.

### E. Nettoyage Système & Hygiène Git
- **Fichiers :** `.DS_Store` (présents à la racine et dans certains sous-dossiers).
- **Action Recommandée :** Supprimer les fichiers `.DS_Store` locaux. Le fichier `.gitignore` les ignore déjà (ligne 15), garantissant qu'ils ne seront jamais indexés.

---

## 5. Matrice Avant / Après de la Racine de PyIngestKit

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| MATRICE DE TRANSFORMATION DE LA RACINE DU PACKAGE                                                 |
+───────────────────────────+──────────────────────+────────────────────────────────────────────────+
| Élément Actuel            | Statut / Action      | Destination Cible / Justification               |
+───────────────────────────+──────────────────────+────────────────────────────────────────────────+
| .DS_Store                 | 🗑️ Supprimer         | Éliminé du système de fichiers local           |
| .editorconfig             | 🔒 Conserver racine  | Configuration globale d'indentation            |
| .env                      | 🔒 Conserver racine  | Variables locales du développeur (git-ignored) |
| .env.example              | 🔒 Conserver racine  | Modèle des variables minimales requises        |
| .git/                     | 🔒 Conserver racine  | Dépôt Git                                      |
| .github/                  | 🔒 Conserver racine  | Workflows CI/CD, issue templates               |
| .gitignore                | 🔒 Conserver racine  | Règles d'exclusion Git                         |
| .mypy_cache/, etc.        | 🔒 Ignoré git        | Caches d'outils de qualité                     |
| AGENTS.md                 | 🔒 Conserver racine  | Instructions agentiques universelles           |
| CHANGELOG.md              | 🔒 Conserver racine  | Journal des modifications et releases           |
| CLAUDE.md                 | 🔒 Conserver racine  | Instructions opérationnelles Claude/IDE        |
| CONTRIBUTING.md           | 🔒 Conserver racine  | Guide de contribution open-source              |
| LICENSE                   | 🔒 Conserver racine  | Licence logicielle (MIT / Apache)              |
| Makefile                  | 🔒 Conserver racine  | Automatisation des commandes standard           |
| README.md                 | 🔒 Conserver racine  | Page d'accueil du dépôt et de PyPI             |
| SECURITY.md               | 🔒 Conserver racine  | Politique de sécurité et signalement vuln.     |
| SHA256SUMS-v0.2.0.txt     | 📦 Déplacer          | docs/releases/archive/SHA256SUMS-v0.2.0.txt     |
| backlog/                  | 🚚 Déplacer / Créer  | docs/build/backlog/ (Cycle SDLC cohérent)       |
| dist/                     | 🔒 Ignoré git        | Artefacts de build wheel/sdist                  |
| docker-compose.staging.yml| 📦 Déplacer          | deployment/docker-compose.staging.yml           |
| docs/                     | 🔒 Conserver racine  | Documentation technique et architecture        |
| envs/                     | 📦 Déplacer          | deployment/envs/                                |
| examples/                 | 🔒 Conserver racine  | Exemples d'usage et tutoriels                   |
| mkdocs.yml                | 🔒 Conserver racine  | Configuration du site de documentation          |
| pyingest-s3.example.yml   | 📦 Déplacer          | examples/configs/pyingest-s3.example.yml        |
| pyingest.yml              | 📦 Déplacer          | examples/configs/pyingest.yml                   |
| pyingest.yml.dev          | 📦 Déplacer          | examples/configs/pyingest.yml.dev               |
| pyingest.yml.example      | 📦 Déplacer          | examples/configs/pyingest.yml.example           |
| pyingest.yml.prod         | 📦 Déplacer          | examples/configs/pyingest.yml.prod              |
| pyingest.yml.stg          | 📦 Déplacer          | examples/configs/pyingest.yml.stg               |
| pyproject.toml            | 🔒 Conserver racine  | Manifeste officiel du package Python            |
| scripts/                  | 🔒 Conserver racine  | Outillage de qualification et de release        |
| src/                      | 🔒 Conserver racine  | Code source du framework hexagonal              |
| tests/                    | 🔒 Conserver racine  | Suites de tests (unit, contract, arch)          |
+───────────────────────────+──────────────────────+────────────────────────────────────────────────+
```

### Arborescence Finale Épurée de la Racine (22 entrées vs 38 initialement)

```text
pyingestkit/
├── .editorconfig
├── .env.example
├── .github/
├── .gitignore
├── AGENTS.md
├── CHANGELOG.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── ROADMAP.md                            <-- Vision macro-produit (miroir pyworkflowkit)
├── SECURITY.md
├── deployment/                           <-- Regroupement de l'infrastructure de test
│   ├── docker-compose.staging.yml
│   └── envs/
├── docs/
│   ├── analyses/
│   ├── architecture/
│   ├── build/
│   │   ├── backlog/                      <-- Backlog technique d'ingénierie
│   │   ├── plans/                        <-- Plans d'implémentation opérationnels
│   │   ├── tasks/                        <-- Tâches atomiques WBS & sessions agentiques
│   │   ├── reports/                      <-- Rapports d'exécution & PV de tests (reports/tests/)
│   │   └── reviews/                      <-- Revues formelles et clôtures de LOT
│   ├── guides/
│   ├── releases/
│   └── roadmap/
├── examples/
│   ├── configs/                          <-- Profils YAML déplacés ici (propre et rangé)
│   ├── customer_360/
│   └── plugin_package/
├── mkdocs.yml
├── pyproject.toml
├── scripts/
├── src/
└── tests/
```

---

## 6. Séquence Opérationnelle d'Implémentation & Vérifications

Pour exécuter cette réorganisation en garantissant **zéro régression**, la séquence suivante doit être observée :

### Étape 1 : Création des répertoires cibles et déplacement Git
```bash
# 1. Backlog technique
mkdir -p docs/build/backlog
if [ -d "backlog" ]; then
    rmdir backlog 2>/dev/null || git mv backlog/* docs/build/backlog/
fi

# 2. Configurations applicatives
mkdir -p examples/configs
git mv pyingest.yml pyingest.yml.dev pyingest.yml.stg pyingest.yml.prod pyingest.yml.example pyingest-s3.example.yml examples/configs/

# 3. Infrastructure et environnements
mkdir -p deployment
git mv docker-compose.staging.yml deployment/
git mv envs deployment/

# 4. Archivage de l'empreinte historique
mkdir -p docs/releases/archive
git mv SHA256SUMS-v0.2.0.txt docs/releases/archive/

# 5. Nettoyage fichiers système
find . -name ".DS_Store" -delete
```

### Étape 2 : Alignement des Références Documentaires
Mettre à jour les documents faisant référence à `docker-compose.staging.yml` et `envs/` :
- [`docs/guides/v1-production-pilot.md`](../guides/v1-production-pilot.md)
- [`docs/reviews/v0.6.0-multienv-profiles-and-s3-object-storage-review.md`](../reviews/v0.6.0-multienv-profiles-and-s3-object-storage-review.md)
- [`deployment/envs/README.md`](../../deployment/envs/README.md) (après déplacement)

### Étape 3 : Fichier d'accueil `docs/build/backlog/README.md`
Créer un fichier de cadrage décrivant le fonctionnement du backlog, le template d'item et le workflow de passage vers `docs/build/plans/`.

### Étape 4 : Validation Stricte des Suites de Tests
Exécuter l'ensemble de la batterie de vérification sous Python 3.13 :
```bash
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make contract-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
```

---

## 7. Conclusion & Recommandations

1. **Backlog :** L'emplacement optimal est **[`docs/build/backlog/`](../build/backlog/)**, complété par le dossier de vision stratégique existant [`docs/roadmap/`](../roadmap/). Cela unifie le flux de delivery (`backlog` -> `plans` -> `reports` -> `reviews`).
2. **Nettoyage de la racine :** Le déplacement des 6 fichiers YAML dans `examples/configs/`, du compose dans `deployment/`, et du dossier `envs/` permet de réduire la racine de **38 à 22 entrées**, atteignant une pureté architecturale identique à `pytransformkit` et `pyworkflowkit`.
3. **Risque opérationnel :** Zéro régression sur le framework ou la suite de tests, les tests contractuels étant déjà isolés dans des environnements `tmp_path`.
