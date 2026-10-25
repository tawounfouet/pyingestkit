# Conventions Opérationnelles & Règles Documentaires : `CONVENTIONS.md`

Ce document centralise les **standards de nommage, conventions d'archivage et règles d'hygiène** appliquées au continuum de développement et de livraison de [`PyIngestKit`](../../README.md).

---

## 1. Convention d'Archivage des Transcripts de Session (`archives/sessions/`)

### A. Rôle & Statut VCS
Lors de l'utilisation de la commande `/transcript`, un historique Markdown exhaustif de la session de pair-programming est produit. 

- **Emplacement cible :** `archives/sessions/`
- **Statut Git obligatoire :** **STRICTEMENT NON VERSIONNÉ** via la règle [`.gitignore`](../../.gitignore) :
  ```gitignore
  /archives/
  ```
- **Justification :** Prévention du gonflement inutile du dépôt Git (*repo bloat* de plusieurs mégaoctets par session), protection contre la fuite d'informations locales, et préservation d'un arbre `docs/` propre et dédié exclusivement aux consommateurs et mainteneurs.

### B. Formule Canonique de Nommage
Chaque fichier de transcript déposé dans `archives/sessions/` doit respecter la structure exacte :

```text
YYYY-MM-DD_session-transcript_<uuid5>_<nom-parlant>.md
```

### C. Décomposition des Segments
| Segment | Format / Type | Exemple | Rôle & Utilité |
| :--- | :--- | :--- | :--- |
| **Date** | `YYYY-MM-DD_` | `2026-10-25_` | Classement chronologique automatique par les outils CLI et navigateurs de fichiers |
| **Racine Type** | `session-transcript_` | `session-transcript_` | Identification univoque de la nature du document (transcript d'échange agentique) |
| **Identifiant Court** | `<uuid5>_` | `bc8cc_` | 5 premiers caractères du `Conversation ID` de la session, garantissant l'unicité stricte en cas de sessions multiples le même jour |
| **Nom Parlant** | `<nom-parlant>` (kebab-case) | `release-v2.2.0-publication-and-governance` | Résumé sémantique concis du sujet, du lot ou de l'objectif traité |
| **Extension** | `.md` | `.md` | Format Markdown standardisé |

### D. Exemple Concret
```text
archives/sessions/2026-10-25_session-transcript_bc8cc_release-v2.2.0-publication-and-governance.md
```

---

## 2. Nomenclature du Continuum SDLC (`docs/build/`)

Chaque étape du cycle d'ingénierie de `PyIngestKit` obéit à un gabarit et une convention de nommage stricts :

| Étape SDLC | Dossier Dédié | Format de Fichier Standard | Modèle Associé |
| :--- | :--- | :--- | :--- |
| **1. Cadrage** | [`backlog/`](./backlog/) | `ITEM-<NUMERO>_<intitule-kebab-case>.md`<br>*Ex: `ITEM-007_advanced-http-acquisition.md`* | [`TEMPLATE_BACKLOG_ITEM.md`](./backlog/TEMPLATE_BACKLOG_ITEM.md) |
| **2. Conception** | [`plans/`](./plans/) | `YYYY-MM-DD_plan-<nom-du-lot>.md`<br>*Ex: `2026-10-25_plan-lot37-advanced-http.md`* | [`TEMPLATE_IMPLEMENTATION_PLAN.md`](./plans/TEMPLATE_IMPLEMENTATION_PLAN.md) |
| **3. Tâches** | [`tasks/`](./tasks/) | `TASK-LOT<XX>-<YY>_<nom-court>.md`<br>*Ex: `TASK-LOT37-01_advanced-http.md`*<br>`TASK-REL-<version>_<nom-court>.md` | [`TEMPLATE_TASK.md`](./tasks/TEMPLATE_TASK.md) |
| **4. Rétroaction** | [`feedback/`](./feedback/) | `FEEDBACK-LOT<XX>-<YY>_<nom-court>.md`<br>`FEEDBACK-REL-<version>_<nom-court>.md` | [`TEMPLATE_FEEDBACK.md`](./feedback/TEMPLATE_FEEDBACK.md) |
| **5. Tests** | [`reports/tests/`](./reports/tests/) | `YYYY-MM-DD_<version-ou-lot>_qualification-test-report.md` | [`TEMPLATE_TEST_REPORT.md`](./reports/tests/TEMPLATE_TEST_REPORT.md) |
| **5 bis. Packaging** | [`reports/dist/`](./reports/dist/) | `YYYY-MM-DD_<version>_distribution-qualification-report.md` | [`TEMPLATE_DIST_REPORT.md`](./reports/dist/TEMPLATE_DIST_REPORT.md) |
| **6. Revues Lots** | [`reviews/`](./reviews/) | `YYYY-MM-DD_<nom-du-lot>_review.md`<br>*Ex: `2026-10-25_lot37_review.md`* | [`TEMPLATE_LOT_REVIEW.md`](./reviews/TEMPLATE_LOT_REVIEW.md) |
| **6 bis. Milestones** | [`reviews/milestones/`](./reviews/milestones/) | `YYYY-MM-DD_milestone-<version>_bilan-cloture.md` | [`TEMPLATE_MILESTONE_REVIEW.md`](./reviews/milestones/TEMPLATE_MILESTONE_REVIEW.md) |

---

## 3. Registres Opérationnels & Tableaux de Bord

1. **Registre des Tâches :** [`tasks/TODOS.md`](./tasks/TODOS.md)
   - Doit être synchronisé à chaque création, modification ou clôture de tâche atomique.
   - Les métriques d'avancement (`TOTAL`, `DONE`, `WIP`, `TODO`, `TAUX DE COMPLÉTION`) doivent être rigoureusement recalculées.
2. **Notes de Version Publiques :** [`docs/releases/`](../releases/)
   - Réservé aux notes de publication consommateur (ex. `v2.2.0.md`).
   - Différent des bilans internes de milestone (réservés à `reviews/milestones/`).

---

## 4. Règles de Discipline Git & Conventional Commits

1. **Préfixes de Commits Recommandés :**
   - `feat(...) :` Nouvelle fonctionnalité du domaine ou connecteur.
   - `fix(...) :` Correction de bug, durcissement ou patch de CI.
   - `docs(...) :` Documentation, plans, tâches, retours d'expérience et conventions.
   - `test(...) :` Ajout ou renforcement de tests unitaires, d'architecture ou de contrats.
   - `chore(...) :` Maintenance d'infrastructure, outillage ou fichiers d'hygiène (`.gitignore`).
2. **Règle Cardinal du *Small Batch* :**
   - Toujours clôturer formellement le lot technique en cours avant d'entamer le lot suivant.
   - Ne jamais mélanger deux chantiers hétérogènes sur la même branche de travail.
