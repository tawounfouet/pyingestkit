# TASK-LOT31-03 : Commande d'Autodiagnostic Système (`pik doctor`)

- **Statut :** ✅ **DONE**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date de complétion :** 2026-10-24
- **Branche Git :** `feat/agentic-governance-and-instructions`

---

## 1. Contexte & Objectif Unitaire

Dans le cadre de l'alignement de la CLI `pik` sur les standards éprouvés de `ptk` (`pytransformkit`) et `pwk` (`pyworkflowkit`), créer la sous-commande `pik doctor`.

Objectifs :
1. **Inspection locale et sans effet de bord** de l'environnement Python, du runtime et de l'installation de `pyingestkit`.
2. **Audit des extras optionnels** : Vérifier la présence et les versions des bibliothèques associées aux extras `cli`, `postgres`, `s3`, `http`, `excel`, `parquet`.
3. **Audit de l'environnement d'exécution** : Localisation du workspace racine, détection des profils d'environnement `.env` (`infra/envs/`, `envs/`, `.env`), et masquage strict des credentials via `redact_sensitive_text`.
4. **Double contrat de rendu TTY / JSON** :
   - Mode interactif : Table Rich soignée avec statuts colorés (OK en vert, OPTIONAL/WARNING en jaune, MISSING en rouge).
   - Mode machine (`--json`) : Émission sur stdout d'un document JSON strict (compatible `jq` et orchestrateurs), logs/alertes redirigés sur stderr.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/cli/commands/doctor.py` | Création | Commande Typer `doctor_command` et logique de diagnostic |
| `src/pyingestkit/cli/commands/__init__.py` | Modification | Export de `doctor_command` |
| `src/pyingestkit/cli/app.py` | Modification | Enregistrement de `doctor` sur l'application Typer `app` |
| `tests/unit/cli/test_doctor.py` | Création | Tests unitaires isolés pour les modes TTY et `--json` |

---

## 3. Checklist d'Exécution

- [x] **1. Écriture de `src/pyingestkit/cli/commands/doctor.py` :**
  - [x] Détecter la version Python courante et vérifier `sys.version_info >= (3, 11)`.
  - [x] Résoudre la version de `pyingestkit`.
  - [x] Auditer les dépendances des extras :
    - [x] `cli` : `typer`, `rich`
    - [x] `postgres` : `sqlalchemy`, `psycopg`
    - [x] `s3` : `boto3`
    - [x] `http` : `httpx`
    - [x] `parquet` : `pyarrow`
    - [x] `excel` : `openpyxl`
  - [x] Auditer l'environnement (`PYINGEST_ENV`, `PYINGEST_CONFIG`, détection des fichiers `.env` dans `infra/envs/`).
  - [x] Implémenter le rendu Rich interactif (`render_human_doctor`).
  - [x] Implémenter le rendu machine (`--json`).
- [x] **2. Câblage de la commande :**
  - [x] Enregistrer `doctor_command` dans `commands/__init__.py` et `app.py`.
- [x] **3. Écriture des tests unitaires `tests/unit/cli/test_doctor.py` :**
  - [x] Tester l'exécution en mode TTY standard (code de retour `ExitCode.SUCCESS`).
  - [x] Tester l'option `--json` et vérifier la validité du JSON produit sur stdout.
  - [x] Mocker une dépendance manquante ou Python non supporté pour vérifier la gestion d'erreur.
- [x] **4. Qualité & Validation :**
  - [x] `ruff check` et `ruff format` : 385 files already formatted.
  - [x] `make architecture-v2` : 79/79 passed.
  - [x] `make contract-v2` : 76/76 passed.
  - [x] `make quality` : mypy 0 issues in 104 files.

---

## 4. Preuves & Commandes de Validation

```bash
# Tests unitaires de la commande doctor
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/test_doctor.py -v
# ============================== 4 passed in 0.28s ===============================

# Ensemble de la suite CLI
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/ -v
# ============================== 22 passed in 0.34s ==============================

# Exécution directe en mode TTY et JSON
PATH="/opt/miniconda3/bin:$PATH" pik doctor
PATH="/opt/miniconda3/bin:$PATH" pik doctor --json
```
