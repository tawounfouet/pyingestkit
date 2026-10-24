# Guide Opérationnel du Framework de Delivery & SDLC : `docs/build/`

Bienvenue dans le guide de référence du **Framework de Delivery & d'Ingénierie Logicielle (SDLC)** de [`PyIngestKit`](../../README.md).

Ce document explique pas-à-pas **comment fonctionne ce framework**, **comment utiliser chaque dossier**, et **comment instancier les templates** pour conduire un chantier de l'expression de besoin jusqu'à la release certifiée.

---

## 1. Philosophie & Vue d'Ensemble du Framework

Ce framework documentaire et opérationnel repose sur le principe de **l'ingénierie pilotée par les spécifications (*spec-driven engineering*)**, optimisée pour le travail collaboratif entre **développeurs humains** et **agents IA** (Antigravity, Claude Code, OpenCode).

### Le Continuum SDLC en 5 Étapes

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| LE CYCLE DE DELIVERY COMPLET DANS DOCS/BUILD/                                                     |
|                                                                                                   |
|  1. BACKLOG          2. PLANS          3. TASKS          4. REPORTS           5. REVIEWS          |
| ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐ |
| │ docs/build/  │──>│ docs/build/  │─>│ docs/build/  │─>│ docs/build/      │─>│ docs/build/      │ |
| │ backlog/     │   │ plans/       │  │ tasks/       │  │ reports/tests/   │  │ reviews/         │ |
| │              │   │              │  │              │  │                  │  │                  │ |
| │ - Quoi faire │   │ - Comment le │  │ - Actions    │  │ - Preuves de     │  │ - Conformité RFC │ |
| │ - Expression │   │   cadencer   │  │   unitaires  │  │   qualification  │  │ - Signature de   │ |
| │   du besoin  │   │ - Architect. │  │ - WBS session│  │ - Couverture code│     clôture de lot  │ |
| │ - Dette tech │   │ - Plan LOT   │  │ - Context IA │  │ - Zero régression│  │ - Autorisation   │ |
| └──────────────┘   └──────────────┘  └──────────────┘  └──────────────────┘  └──────────────────┘ |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Cartographie des Dossiers & des Templates Dédiés

Chaque dossier du cycle possède un rôle strict et son template de référence :

| Étape | Dossier Dédié | Rôle & Contenu | Template Associé |
| :--- | :--- | :--- | :--- |
| **0. Benchmark** | [`docs/analyses/`](../analyses/) | Études comparatives, audits d'architecture, benchmarks siblings | [`TEMPLATE_ANALYSIS.md`](../analyses/TEMPLATE_ANALYSIS.md) |
| **1. Cadrage** | [`docs/build/backlog/`](./backlog/) | Besoins bruts, user stories, signalements de dette technique | [`TEMPLATE_BACKLOG_ITEM.md`](./backlog/TEMPLATE_BACKLOG_ITEM.md) |
| **2. Conception** | [`docs/build/plans/`](./plans/) | Plans directeurs d'implémentation par LOT technique | [`TEMPLATE_IMPLEMENTATION_PLAN.md`](./plans/TEMPLATE_IMPLEMENTATION_PLAN.md) |
| **3. Exécution** | [`docs/build/tasks/`](./tasks/) | Tâches atomiques de session, checklists WBS ciblées | [`TEMPLATE_TASK.md`](./tasks/TEMPLATE_TASK.md) |
| **4. Validation** | [`docs/build/reports/tests/`](./reports/tests/) | Procès-verbaux d'exécution, matrices de recette, couverture | [`TEMPLATE_TEST_REPORT.md`](./reports/tests/TEMPLATE_TEST_REPORT.md) |
| **5. Clôture** | [`docs/build/reviews/`](./reviews/) | Audit de conformité, signatures formelles et merge autorisés | [`TEMPLATE_LOT_REVIEW.md`](./reviews/TEMPLATE_LOT_REVIEW.md) |

---

## 3. Playbook Pas-à-Pas : Comment Utiliser le Framework

### Scénario 1 : J'ai une nouvelle idée, un besoin client ou une dette à signaler
1. **Créer la fiche de backlog :**
   ```bash
   cp docs/build/backlog/TEMPLATE_BACKLOG_ITEM.md docs/build/backlog/ITEM-2026-10-25_mon-besoin.md
   ```
2. **Remplir les sections clés :**
   - Contexte et problème constaté.
   - User Story (*En tant que... je souhaite... afin de...*).
   - Invariants à respecter (11 symboles de la racine, non-régression).
3. **Statut initial :** `PROPOSED`.
4. Lors de l'arbitrage, passer le statut à `ACCEPTED` ou `PLANNED`.

---

### Scénario 2 : Je planifie un nouveau chantier ou LOT technique
1. **Si un arbitrage d'architecture est requis :**
   - Créer une analyse comparative :
     ```bash
     cp docs/analyses/TEMPLATE_ANALYSIS.md docs/analyses/2026-10-25_mon-analyse.md
     ```
   - Comparer les patterns avec [`pytransformkit`](../../../pytransformkit) et [`pyworkflowkit`](../../../pyworkflowkit).
2. **Rédiger le Plan Directeur d'Implémentation :**
   ```bash
   cp docs/build/plans/TEMPLATE_IMPLEMENTATION_PLAN.md docs/build/plans/2026-10-25_plan-mon-chantier.md
   ```
3. **Définir :**
   - Les capacités livrées et les exclusions hors périmètre.
   - Le diagramme d'architecture ASCII.
   - Les phases séquentielles (Phase 1, Phase 2, etc.).
   - La matrice de risques et la checklist de qualification finale.

---

### Scénario 3 : J'exécute une session de développement (avec ou sans Agent IA)
1. **Découper le plan en tâches atomiques dans `tasks/` :**
   ```bash
   cp docs/build/tasks/TEMPLATE_TASK.md docs/build/tasks/TASK-LOT33-01_ma-tache.md
   ```
2. **Remplir la fiche unitaire :**
   - Cible resserrée (1 à 3 fichiers de code, 1 fichier de test).
   - Checklist granulaire étape par étape.
   - Commande de test unitaire rapide.
3. **Optimisation pour Agent IA :**
   - Donner uniquement la fiche `TASK-LOT33-01_ma-tache.md` à l'agent IA comme consigne.
   - L'agent n'a pas besoin de lire l'intégralité du plan parent de 500 lignes : **gain massif de tokens et zéro hallucination**.
4. **Passage d'état :** `TODO` ➔ `IN_PROGRESS` ➔ `DONE`.
5. **En fin de tâche :** Renseigner le SHA du commit et les résultats de tests dans la section 5 de la tâche.

---

### Scénario 4 : Je certifie les tests et prépare la livraison
1. **Créer le rapport de qualification :**
   ```bash
   cp docs/build/reports/tests/TEMPLATE_TEST_REPORT.md docs/build/reports/tests/2026-10-25_lot33_test-report.md
   ```
2. **Exécuter les batteries officielles de tests :**
   ```bash
   # 1. Frontières d'architecture hexagonale & 11 symboles
   PATH="/opt/miniconda3/bin:$PATH" make architecture-v2

   # 2. Contrats de stabilité et fixtures JSON
   PATH="/opt/miniconda3/bin:$PATH" make contract-v2

   # 3. Suite complète unitaire et intégration
   PATH="/opt/miniconda3/bin:$PATH" make test-v2

   # 4. Linting et formatage
   PATH="/opt/miniconda3/bin:$PATH" make quality
   ```
3. **Consigner les résultats** dans le rapport (durée, nombre de tests, logs d'exécution).

---

### Scénario 5 : Je clôture formellement le lot et autorise la release
1. **Créer la revue de lot :**
   ```bash
   cp docs/build/reviews/TEMPLATE_LOT_REVIEW.md docs/build/reviews/2026-10-25_lot33_release-review.md
   ```
2. **Auditer la grille de conformité :**
   - Architecture hexagonale vérifiée ? ✅
   - API racine V2 inviolée ? ✅
   - Fixtures de contrat intactes ? ✅
   - Sécurité et absence de secrets vérifiées ? ✅
   - Documentation et guides à jour ? ✅
3. **Signer formellement :** Passer le statut à `APPROUVÉ POUR MERGE & RELEASE`.
4. Procéder au merge de la PR, à la création du tag Git et à la publication PyPI.

---

## 4. Règles d'Or & Invariants Non-Négociables

Tout utilisateur ou agent opérant dans ce framework **DOIT IMPÉRATIVEMENT** respecter les règles suivantes :

1. **Inviolabilité de l'API Racine V2 :**
   L'API publique exportée dans [`src/pyingestkit/__init__.py`](../../src/pyingestkit/__init__.py) est **strictement gelée à 11 symboles**. Ne jamais élargir ou réintroduire d'anciennes classes V1 (`Job`, `Pipeline`, `Runner`) à la racine.
2. **Sanctuarisation des Fixtures de Contrat :**
   Ne **jamais modifier** les fixtures JSON sous `tests/contract/fixtures/` pour faire passer un test en échec. C'est l'implémentation qui doit s'adapter au contrat, jamais l'inverse.
3. **Le Code de Test reste à la Racine :**
   Le code Python de test vit exclusivement dans [`tests/`](../../tests/). Seuls les procès-verbaux et rapports Markdown vivent dans `docs/build/reports/tests/`.
4. **Liens Relatifs Stricts :**
   Tous les liens dans les fichiers Markdown doivent être des **chemins relatifs** (`../plans/...`, `../../README.md`). Ne jamais utiliser d'URL absolue de machine locale (`file:///Users/...`).
5. **Nomenclature Temporelle Standardisée :**
   Les fichiers d'analyses et de plans portent impérativement le préfixe de date avec tiret bas : `YYYY-MM-DD_<intitule>.md`.

---

## 5. Aide-Mémoire des Commandes Utiles

```bash
# Vérifier l'architecture et les frontières
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2

# Vérifier les contrats d'API publique
PATH="/opt/miniconda3/bin:$PATH" make contract-v2

# Exécuter l'ensemble des 367 tests V2
PATH="/opt/miniconda3/bin:$PATH" make test-v2

# Formater et vérifier la syntaxe
PATH="/opt/miniconda3/bin:$PATH" ruff format . && ruff check .

# Compiler la documentation en mode strict
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```
