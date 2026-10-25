# Registre Central des Tâches Opérationnelles : `TODOS.md`

Ce document constitue le **tableau de bord opérationnel centralisé** des tâches de développement, de refactorisation et de gouvernance du package [`PyIngestKit`](../../../README.md).

---

## 1. Métriques & Tableau de Bord d'Avancement

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TABLEAU DE BORD D'AVANCEMENT GLOBAL DES TÂCHES                                                   │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┬──────────────────────────┤
│ TOTAL TÂCHES    │ TERMINÉES (DONE)│ EN COURS (WIP)  │ À FAIRE (TODO)  │ TAUX DE COMPLÉTION       │
│ 8               │ 7               │ 1               │ 0               │ 87.5 % [██████████████░░]│
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴──────────────────────────┘
```

---

## 2. Matrice Globale des Tâches Opérationnelles

| Réf. Tâche | Intitulé & Périmètre | LOT | Item Backlog | Composant | Assigné | Statut | Créé | Clôturé | Commit | Fiche Feedback |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| [`TASK-LOT30-01`](./TASK-LOT30-01_agentic-framework-governance.md) | Gouvernance Agentique (`AGENTS.md` + `CLAUDE.md`) | LOT-30 | - | Gouvernance | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`947ffc1`](https://github.com/) | - |
| [`TASK-LOT32-01`](./TASK-LOT32-01_root-hygiene-and-profile-reorganization.md) | Assainissement racine & isolation stack `infra/` | LOT-32 | [`ITEM-002`](../backlog/ITEM-002_root-cleanup-and-profile-reorganization.md) | Structure Repo | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`2fbad5b`](https://github.com/) | [`FEEDBACK-LOT32-01`](../feedback/FEEDBACK-LOT32-01_root-hygiene-reorganization.md) |
| [`TASK-LOT31-01`](./TASK-LOT31-01_cli-bootstrap-and-exit-codes.md) | Bootstrap CLI stdlib & Exit Codes `IntEnum` | LOT-31 | [`ITEM-001`](../backlog/ITEM-001_cli-pik-standardization.md) | CLI (`pik`) | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`011a806`](https://github.com/) | [`FEEDBACK-LOT31-01`](../feedback/FEEDBACK-LOT31-01_cli-bootstrap-and-exit-codes.md) |
| [`TASK-LOT31-02`](./TASK-LOT31-02_cli-security-and-credentials-redaction.md) | Sécurité Filesystem & Redaction des Credentials | LOT-31 | [`ITEM-001`](../backlog/ITEM-001_cli-pik-standardization.md) | CLI (`pik`) | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`9ccfd3b`](https://github.com/) | [`FEEDBACK-LOT31-02`](../feedback/FEEDBACK-LOT31-02_cli-security-and-credentials-redaction.md) |
| [`TASK-LOT31-03`](./TASK-LOT31-03_cli-doctor-diagnostic-command.md) | Commande d'Autodiagnostic Système (`pik doctor`) | LOT-31 | [`ITEM-001`](../backlog/ITEM-001_cli-pik-standardization.md) | CLI (`pik`) | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`040d5af`](https://github.com/) | [`FEEDBACK-LOT31-03`](../feedback/FEEDBACK-LOT31-03_cli-doctor-diagnostic-command.md) |
| [`TASK-LOT33-01`](./TASK-LOT33-01_brand-identity-assets-integration.md) | Intégration globale brand assets & charte visuelle | LOT-33 | [`ITEM-003`](../backlog/ITEM-003_brand-assets-and-visual-identity.md) | Design System | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-24 | [`e4349a0`](https://github.com/) | [`FEEDBACK-LOT33-01`](../feedback/FEEDBACK-LOT33-01_brand-identity-assets-integration.md) |
| [`TASK-LOT34-01`](./TASK-LOT34-01_pypi-oidc-release-automation.md) | Automatisation Release PyPI OIDC & Supply Chain | LOT-34 | [`ITEM-004`](../backlog/ITEM-004_pypi-supply-chain-and-release-automation.md) | CI/CD & Supply Chain | AWF / Antigravity | ✅ **DONE** | 2026-10-24 | 2026-10-25 | [`PR#70`](https://github.com/) | [`FEEDBACK-LOT34-01`](../feedback/FEEDBACK-LOT34-01_pypi-oidc-release-automation.md) |
| [`TASK-LOT35-01`](./TASK-LOT35-01_replay-provenance-and-historical-reconstruction.md) | Provenance Replay & Reconstruction Historique d'Ingestion | LOT-35 | [`ITEM-005`](../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md) | Core Domain & Replay | AWF / Antigravity | 🚧 **IN_PROGRESS** | 2026-10-25 | - | - | - |

---

## 3. File d'Attente des Prochaines Tâches (Roadmap Prévisionnelle)

Les tâches ci-dessous sont issues des items de backlog approuvés et seront activées au fil des jalons :

| Réf. Future Tâche | Intitulé Prévu | LOT | Item Backlog | Priorité | Statut |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `TASK-LOT36-01` | Adaptateur PostgreSQL UPSERT/MERGE et staging transactionnel | LOT-36 | [`ITEM-006`](../backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md) | MOYENNE | 💡 **CANDIDAT** |
| `TASK-LOT37-01` | Client HTTP durci avec validation anti-SSRF et retry exponentiel | LOT-37 | [`ITEM-007`](../backlog/ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md) | MOYENNE | 💡 **CANDIDAT** |

---

## 4. Protocole de Mise à Jour de `TODOS.md`

Toute session de développement agentique ou humaine doit synchroniser ce fichier selon la règle d'or :

1. **Création d'une tâche :**
   - Créer le fichier `TASK-LOTxx-yy_<nom>.md` via [`TEMPLATE_TASK.md`](./TEMPLATE_TASK.md).
   - Ajouter la ligne dans la section 2 avec le statut `📋 TODO` ou `🚧 IN_PROGRESS`.
   - Incrémenter le total dans le tableau de bord des métriques.
2. **Fin d'implémentation & validation :**
   - Mettre à jour le fichier de tâche à `✅ DONE` avec les preuves d'exécution.
   - Rédiger la fiche REX correspondante dans [`docs/build/feedback/`](../feedback/).
   - Mettre à jour la ligne dans `TODOS.md` avec la date de clôture, le commit SHA et le lien vers la fiche de feedback.
   - Mettre à jour le compteur des tâches terminées et le taux de complétion.
3. **Clôture formelle de Jalon (Règle « Clôturer avant de poursuivre ») :**
   - Dès qu'un LOT entier est complété à 100% (toutes ses tâches à `✅ DONE`), le jalon doit être audité via une revue formelle dans [`docs/build/reviews/`](../reviews/).
   - La branche du lot doit être poussée et fusionnée dans `main`.
   - La branche suivante doit impérativement être créée à partir du `main` mis à jour avant d'entamer les tâches du lot suivant. Voir [`docs/build/reviews/README.md`](../reviews/README.md).
