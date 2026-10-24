# TASK-LOT30-01 : Mise en Place de la Gouvernance Agentique (`AGENTS.md` & `CLAUDE.md`)

- **Statut :** ✅ **DONE**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-agentic-framework-integration.md`](../plans/2026-10-24_plan-agentic-framework-integration.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date d'achèvement :** 2026-10-24
- **Branche Git :** `feat/agentic-governance-and-instructions`
- **Commit SHA :** `2b33a21`

---

## 1. Contexte & Objectif Unitaire

Formaliser le socle d'instructions agentiques canonique à la racine de [`PyIngestKit`](../../../README.md), en comblant le retard d'alignement avec les packages frères [`pytransformkit`](../../../../pytransformkit) et [`pyworkflowkit`](../../../../pyworkflowkit).

La tâche impose :
1. Verrouiller les **invariants non-négociables** (API racine V2 gelée à 11 symboles, dual-ledger, Compare-and-Swap, fixtures de contrat intouchables).
2. Fournir un protocole de session interactif standardisé (*pre-flight checklist*, outillage de validation).

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `AGENTS.md` | Création | Instructions universelles pour agents IA (Gemini, Claude, OpenCode, Cursor) et développeurs humains |
| `CLAUDE.md` | Création | Surcouche opérationnelle pour Claude Code et assistants de session interactive |

---

## 3. Checklist d'Exécution

- [x] Rédiger `AGENTS.md` à la racine :
  - [x] Définir la baseline officielle (v2.1.0 publiée).
  - [x] Sanctuariser l'API racine V2 (11 symboles : `IngestionRuntime`, `IngestionPlan`, `RunContext`, `RunResult`, `Source`, `PublicationLedger`, `PublicationRecord`, `DatasetRef`, `RunStatus`, `VersionStrategy`, `IngestionError`).
  - [x] Interdire la modification des fixtures de contrat sous `tests/contract/fixtures/`.
  - [x] Décrire la politique de logging, typage strict et gestion des erreurs RFC-001.
- [x] Rédiger `CLAUDE.md` à la racine :
  - [x] Référencer `AGENTS.md` en amont obligatoire.
  - [x] Établir la checklist pre-flight en 7 étapes.
  - [x] Documenter les commandes `Makefile` officielles (`make architecture-v2`, `make contract-v2`, `make test-v2`).
- [x] Exécuter la suite complète de vérification de non-régression.
- [x] Commiter sur la branche `feat/agentic-governance-and-instructions`.

---

## 4. Preuves & Commandes de Validation

```bash
# Vérification des frontières architecturales et des 11 symboles
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
# Résultat : 79 passed in 0.44s ✅

# Vérification du contrat de stabilité V1/V2
PATH="/opt/miniconda3/bin:$PATH" make contract-v2
# Résultat : 76 passed in 0.38s ✅

# Exécution de l'intégralité de la suite V2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
# Résultat : 367 passed, 25 skipped in 3.43s ✅
```

---

## 5. Résultat & Preuve d'Exécution

- Fichiers créés : [`AGENTS.md`](../../../AGENTS.md) (6 384 octets) et [`CLAUDE.md`](../../../CLAUDE.md) (2 534 octets).
- Commit de scellement : `2b33a21` (`feat(governance): add AGENTS.md and CLAUDE.md instructions for agentic framework parity`).
- Régression constatée : **0**.
