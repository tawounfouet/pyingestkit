# TASK-LOT31-01 : Bootstrap CLI Stdlib Léger & Codes de Sortie Processus

- **Statut :** ✅ **DONE**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date de complétion :** 2026-10-24
- **Branche Git :** `feat/agentic-governance-and-instructions`

---

## 1. Contexte & Objectif Unitaire

Dans le cadre de la standardisation de la CLI [`pik`](../../../pyproject.toml) sur les patterns de `ptk` et `pwk`, doter PyIngestKit d'un point d'entrée ultra-léger basé exclusivement sur la bibliothèque standard Python (`sys`, `os`, `importlib.util`).

Objectifs techniques :
1. **Zéro dépendance lourde au démarrage** : Ne pas importer `typer` ou `rich` avant de savoir s'ils sont disponibles.
2. **Gestion gracieuse des extras manquants** : Si l'extra `[cli]` n'est pas installé, afficher un message d'installation explicite (`pip install "pyingestkit[cli]"`) et sortir immédiatement avec le code `ExitCode.MISSING_OPTIONAL_DEPENDENCY` (11), sans traceback.
3. **Capture des signaux Unix** : Intercepter `BrokenPipeError` (`EPIPE`) et retourner le code `141`.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `src/pyingestkit/cli/exit_codes.py` | Création | Définition de l'énumération `ExitCode(IntEnum)` stable |
| `src/pyingestkit/cli/bootstrap.py` | Création | Point d'entrée `main()` stdlib avec vérification `find_spec` et guard pipes |
| `src/pyingestkit/cli/main.py` | Modification | Redirection transparente vers `bootstrap.main()` |
| `src/pyingestkit/cli/__init__.py` | Modification | Import lazy `app` via PEP 562 `__getattr__` |
| `tests/unit/cli/test_exit_codes.py` | Création | Test d'immutabilité et de cohérence des codes d'erreur |
| `tests/unit/cli/test_bootstrap.py` | Création | Tests de l'interception de dépendances manquantes et de pipes |

---

## 3. Checklist d'Exécution

- [x] **1. Écrire `exit_codes.py`** :
  - [x] `SUCCESS = 0`
  - [x] `GENERAL_ERROR = 1`
  - [x] `VALIDATION_ERROR = 2`
  - [x] `EXECUTION_FAILURE = 3`
  - [x] `SECURITY_ERROR = 4`
  - [x] `MISSING_OPTIONAL_DEPENDENCY = 11`
  - [x] `FILESYSTEM_ERROR = 12`
  - [x] `INTERNAL_ERROR = 70`
  - [x] `INTERRUPTED = 130`
  - [x] `BROKEN_PIPE = 141`
- [x] **2. Écrire `bootstrap.py`** :
  - [x] Vérifier `importlib.util.find_spec("typer")` et `find_spec("rich")`.
  - [x] Capter `BrokenPipeError` et protéger le descripteur de capture sous pytest.
  - [x] Capter `KeyboardInterrupt` et retourner `ExitCode.INTERRUPTED`.
- [x] **3. Adapter `src/pyingestkit/cli/main.py`** et `__init__.py` :
  - [x] Déléguer l'exécution à `from pyingestkit.cli.bootstrap import main`.
  - [x] Lazy import de `app` via `__getattr__`.
- [x] **4. Rédiger les tests unitaires sous `tests/unit/cli/`** :
  - [x] Valider chaque valeur de `ExitCode`.
  - [x] Mocker `importlib.util.find_spec` pour simuler l'absence de `typer` et vérifier la sortie stdout/stderr et le code de retour 11.
- [x] **5. Vérifier la non-régression globale** :
  - [x] Exécuter `make architecture-v2` (79/79 passed).
  - [x] Exécuter `make contract-v2` (76/76 passed).
  - [x] Exécuter `make test-v2` (367 passed, 25 skipped).
  - [x] Exécuter `make quality` (ruff + mypy 104 files 0 errors).

---

## 4. Preuves & Commandes de Validation

```bash
# Tests unitaires de la CLI
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/ -v
# ============================== 9 passed in 0.38s ===============================

# Suites de régression V2
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
# 79 passed in 1.29s

PATH="/opt/miniconda3/bin:$PATH" make contract-v2
# 76 passed in 0.43s

PATH="/opt/miniconda3/bin:$PATH" make quality
# All checks passed! 383 files already formatted. Success: no issues found in 104 source files.
```
