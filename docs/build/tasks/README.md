# Gouvernance des Tâches Opérationnelles (WBS) : `docs/build/tasks/`

Ce répertoire héberge les **fiches de tâches atomiques** (*Work Breakdown Structure*) exécutées au fil des sessions de développement et de pair-programming agentique.

---

## 1. Rôle & Granularité

Dans le continuum d'ingénierie de `PyIngestKit`, les tâches représentent le **troisième niveau de décomposition** :

```text
1. Backlog (docs/build/backlog/)       ──> Quoi faire ? (Besoins bruts & dettes)
2. Plans (docs/build/plans/)           ──> Comment cadencer ? (Plans directeurs par LOT)
3. Tâches (docs/build/tasks/)          ──> Quelle action mener ? (Fiches de session atomiques)
4. Rapports (docs/build/reports/)      ──> Preuves d'exécution & validation tests
5. Revues (docs/build/reviews/)        ──> Signatures de conformité & clôture de lot
```

Une tâche :
- Découpe une phase ou une sous-étape précise d'un **Plan Directeur** ([`docs/build/plans/`](../plans/)).
- Cible un périmètre resserré (1 à 4 fichiers modifiés ou créés).
- Optimise la fenêtre de contexte des agents IA (Antigravity, Claude Code, OpenCode) en fournissant uniquement le contexte nécessaire.
- Comporte sa propre commande de validation unitaire (`pytest`, `make`).

> [!TIP]
> **Registre Central d'Avancement :**
> Pour consulter la matrice complète de toutes les tâches, leurs métriques d'avancement, statuts en direct et liens vers les fiches de feedback, référez-vous au document central : [**`TODOS.md`**](./TODOS.md).

---

## 2. Convention de Nommage & Nomenclature

Chaque fichier de tâche respecte la syntaxe suivante :

```text
TASK-LOT<NUMERO_LOT>-<INDEX_TACHE>_<intitule-court-kebab-case>.md
```

### Exemples :
- `TASK-LOT30-01_agentic-framework-governance.md`
- `TASK-LOT31-01_cli-bootstrap-and-exit-codes.md`
- `TASK-LOT31-02_cli-security-and-credentials-redaction.md`
- `TASK-LOT32-01_root-hygiene-and-profile-reorganization.md`

---

## 3. États & Cycle de Vie d'une Tâche

Toute tâche traverse 4 états déterministes :

```text
┌────────┐      ┌─────────────┐      ┌──────────┐
│  TODO  │ ───> │ IN_PROGRESS │ ───> │   DONE   │
└────────┘      └─────────────┘      └──────────┘
    │                                      ▲
    ▼                                      │
┌─────────┐                                │
│ BLOCKED │ ───────────────────────────────┘
└─────────┘
```

- **`TODO`** : Tâche spécifiée, prête à être prise en charge.
- **`IN_PROGRESS`** : En cours de réalisation par un développeur ou un agent IA.
- **`BLOCKED`** : Suspendue en attente d'un arbitrage ou d'une dépendance amont.
- **`DONE`** : Implémentée, testée, validée sans régression et commitée.

---

## 4. Gabarit Standard d'une Fiche de Tâche

```markdown
# TASK-LOT<XX>-<YY> : <Titre Explicite de la Tâche>

- **Statut :** TODO | IN_PROGRESS | DONE | BLOCKED
- **Plan Parent :** [docs/build/plans/YYYY-MM-DD_plan-xxxx.md](../plans/YYYY-MM-DD_plan-xxxx.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** YYYY-MM-DD
- **Date d'achèvement :** YYYY-MM-DD (si DONE)
- **Branche Git :** feat/nom-de-la-branche

---

## 1. Contexte & Objectif Unitaire
Description concise de la valeur ajoutée et de l'inviolabilité architecturale à respecter.

## 2. Périmètre des Fichiers
- `src/pyingestkit/...` (Création / Modification)
- `tests/unit/...` (Tests unitaires associés)

## 3. Checklist d'Exécution
- [ ] Étape 1 : Implémentation du module ou composant.
- [ ] Étape 2 : Écriture de la suite de tests unitaires isolée.
- [ ] Étape 3 : Exécution de la commande de validation.
- [ ] Étape 4 : Formatage et linting (`ruff check`, `ruff format`).

## 4. Preuves & Commandes de Validation
```bash
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/mon_module/test_mon_module.py -v
```

## 5. Résultat & Preuve d'Exécution (si DONE)
- Commit SHA : `abcdef12`
- Résumé des tests passés.
```

---

## 5. Index des Tâches Actuelles

| Réf. Tâche | Intitulé | Plan Associé | Statut |
| :--- | :--- | :--- | :--- |
| [`TASK-LOT30-01`](./TASK-LOT30-01_agentic-framework-governance.md) | Gouvernance Agentique (`AGENTS.md` + `CLAUDE.md`) | [Plan Agentique](../plans/2026-10-24_plan-agentic-framework-integration.md) | ✅ **DONE** |
| [`TASK-LOT31-01`](./TASK-LOT31-01_cli-bootstrap-and-exit-codes.md) | Bootstrap CLI stdlib & Exit Codes IntEnum | [Plan CLI pik](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md) | ✅ **DONE** |
| [`TASK-LOT31-02`](./TASK-LOT31-02_cli-security-and-credentials-redaction.md) | Sécurité Filesystem & Masquage des Secrets | [Plan CLI pik](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md) | ✅ **DONE** |
| [`TASK-LOT31-03`](./TASK-LOT31-03_cli-doctor-diagnostic-command.md) | Commande d'Autodiagnostic Système (`pik doctor`) | [Plan CLI pik](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md) | ✅ **DONE** |
| [`TASK-LOT32-01`](./TASK-LOT32-01_root-hygiene-and-profile-reorganization.md) | Nettoyage de la Racine & Migration des Profils YAML | [Analyse Hygiène Racine](../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md) | ✅ **DONE** |
