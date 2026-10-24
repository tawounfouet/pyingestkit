# Plan d'Implémentation : <Titre du Chantier ou LOT Technique>

<!-- 
NOMENCLATURE DU FICHIER :
docs/build/plans/YYYY-MM-DD_plan-<intitule-kebab-case>.md
Exemple : docs/build/plans/2026-10-25_plan-parquet-streaming-writer.md
-->

- **Projet :** PyIngestKit
- **Statut :** DRAFT <!-- DRAFT | READY | IN_PROGRESS | DONE -->
- **Date :** YYYY-MM-DD
- **Auteur :** <!-- Antigravity / Pair Programming / Nom -->
- **Document source :** [`../../analyses/YYYY-MM-DD_mon-analyse.md`](../../analyses/)
- **Références amont :** <!-- Liens relatifs vers pytransformkit / pyworkflowkit / specs -->
- **Branche cible :** `feat/<nom-de-branche>`

---

## 1. Objectifs & Périmètre

<!-- 
Définir de manière concise ce que ce plan livre et ce qui est explicitement hors périmètre.
-->

### Capacités Livrées
1. **Capacité 1 :** ...
2. **Capacité 2 :** ...
3. **Capacité 3 :** ...

### Hors Périmètre (Exclusions Délibérées)
- Non-objectif 1 : ...
- Non-objectif 2 : ...

---

## 2. Diagramme d'Architecture & Flux de Données

<!-- 
Insérer un diagramme ASCII soigné modélisant les flux, composants ou couches hexagonales.
-->

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| FLUX D'EXÉCUTION OU D'ARCHITECTURE DU SYSTÈME                                                     |
|                                                                                                   |
|  [ Composant Amont / Déclencheur ]                                                                 |
|                 │                                                                                 |
|                 ▼                                                                                 |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Couche Applicative / Orchestrateur                                                          |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                 │                                                                                 |
|                 ▼                                                                                 |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Cœur de Domaine Hexagonal (Zero-I/O, Invariants immuables)                                   |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                 │                                                                                 |
|        ┌────────┴────────┐                                                                        |
|        ▼                 ▼                                                                        |
|  [ Port Adaptateur A ]  [ Port Adaptateur B ]                                                     |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

<!-- 
Inventaire exhaustif des fichiers créés, modifiés ou supprimés.
-->

```text
src/pyingestkit/
├── .../mon_module.py                    # [CRÉATION] <Description unitaire>
└── .../existant.py                     # [MODIFICATION] <Description de l'ajustement>

tests/
├── unit/.../test_mon_module.py         # [CRÉATION] Tests unitaires isolés
└── contract/.../test_mon_contrat.py    # [MODIFICATION / VALIDATION] Tests de contrat

docs/
└── guides/...                          # [CRÉATION] Documentation utilisateur associée
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — <Nom de la Phase 1>
**Tâche associée :** [`../tasks/TASK-LOTXX-01_description.md`](../tasks/)  
**Fichiers :** `src/...`

#### Détails d'implémentation
```python
# Extrait de code d'interface ou de signature attendue
```

---

### Phase 2 — <Nom de la Phase 2>
**Tâche associée :** [`../tasks/TASK-LOTXX-02_description.md`](../tasks/)  
**Fichiers :** `src/...`

---

## 5. Matrice de Risques & Stratégie de Rollback

| Risque Identifié | Gravité | Probabilité | Mesure d'Atténuation | Procédure de Rollback |
| :--- | :--- | :--- | :--- | :--- |
| Régression sur l'API racine V2 | Critique | Faible | Test `make architecture-v2` bloquant en pre-commit | `git revert <sha>` |
| Dérive de schéma ou de contrat | Élevée | Faible | Test `make contract-v2` sur fixtures JSON immuables | Annulation de PR |

---

## 6. Checklist de Qualification & Validation

<!-- 
Commandes exactes que l'agent ou le développeur doit exécuter avant merge.
-->

- [ ] **Tests d'Architecture :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
  ```
- [ ] **Tests de Contrat :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make contract-v2
  ```
- [ ] **Suite Complète V2 :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make test-v2
  ```
- [ ] **Contrôle Qualité & Typage :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make quality
  ```
