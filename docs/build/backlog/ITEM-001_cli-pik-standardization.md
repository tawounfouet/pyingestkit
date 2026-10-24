# ITEM-001 : Standardisation de la CLI PyIngestKit (`pik`) & Bootstrap Résilient

- **Statut :** PLANNED
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** HAUTE
- **Composant Cible :** CLI (`src/pyingestkit/cli/`)
- **Plan Associé :** [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **LOT Cible :** LOT-31 (v2.1.1 / v2.2.0)

---

## 1. Contexte & Problématique Constatée

Actuellement, l'interface en ligne de commande de `PyIngestKit` présente un retard d'ergonomie et d'alignement par rapport aux packages frères [`pytransformkit`](../../../../pytransformkit) (`ptk`) et [`pyworkflowkit`](../../../../pyworkflowkit) (`pwk`) :
1. L'alias court officiel `pik` n'est pas enregistré dans `pyproject.toml: [project.scripts]`.
2. Le point d'entrée charge directement des dépendances tierces sans guard stdlib au démarrage.
3. Les codes de sortie processus ne sont pas strictement typés via une `IntEnum`.
4. L'absence de commande d'autodiagnostic (`doctor`) complique le dépannage en environnement client.

---

## 2. Expression du Besoin & User Story

- **En tant que :** Développeur de pipeline ou orchestrateur externe (Airflow, Dagster, Bash).
- **Je souhaite :** Disposer de la commande console `pik` rapide, robuste, avec codes de retour déterministes et autodiagnostic.
- **Afin de :** Piloter mes ingestions de manière fiable et standardisée à travers tout le monorepo.

---

## 3. Bénéfices Attendus

1. **Ergonomie :** Raccourci `pik` aligné sur `ptk` et `pwk`.
2. **Robustesse :** Zéro traceback si `typer` ou `rich` est manquant (message d'installation guidé).
3. **Automatisation :** Mode machine `--json` stable sur stdout et codes d'erreur conformes Unix (`0`, `1`, `2`, `11`, `141`).

---

## 4. Invariants Architecturaux

- [x] Le Core Domain de PyIngestKit reste 100 % agnostique de la CLI et de Typer.
- [x] L'API racine V2 (`__init__.py`) demeure gelée à ses 11 symboles officiels.
- [x] Le bootstrap de démarrage (`bootstrap.py`) n'utilise QUE la bibliothèque standard Python (`importlib.util`).

---

## 5. Livrables Associés

- Plan d'implémentation : [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- Tâche initiale : [`docs/build/tasks/TASK-LOT31-01_cli-bootstrap-and-exit-codes.md`](../tasks/TASK-LOT31-01_cli-bootstrap-and-exit-codes.md)
