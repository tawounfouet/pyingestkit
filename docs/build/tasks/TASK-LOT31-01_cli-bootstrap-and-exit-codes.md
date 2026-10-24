# TASK-LOT31-01 : Bootstrap CLI Stdlib Léger & Codes de Sortie Processus

- **Statut :** 📋 **TODO**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Branche Git :** `feat/cli-pik-standardization-and-bootstrap`

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
| `tests/unit/cli/test_exit_codes.py` | Création | Test d'immutabilité et de cohérence des codes d'erreur |
| `tests/unit/cli/test_bootstrap.py` | Création | Tests de l'interception de dépendances manquantes et de pipes |

---

## 3. Checklist d'Exécution

- [ ] **1. Écrire `exit_codes.py`** :
  - [ ] `SUCCESS = 0`
  - [ ] `GENERAL_ERROR = 1`
  - [ ] `VALIDATION_ERROR = 2`
  - [ ] `EXECUTION_FAILURE = 3`
  - [ ] `SECURITY_ERROR = 4`
  - [ ] `MISSING_OPTIONAL_DEPENDENCY = 11`
  - [ ] `FILESYSTEM_ERROR = 12`
  - [ ] `INTERNAL_ERROR = 70`
  - [ ] `INTERRUPTED = 130`
  - [ ] `BROKEN_PIPE = 141`
- [ ] **2. Écrire `bootstrap.py`** :
  - [ ] Vérifier `importlib.util.find_spec("typer")` et `find_spec("rich")`.
  - [ ] Capter `BrokenPipeError` et réassigner `stderr = devnull`.
  - [ ] Capter `KeyboardInterrupt` et retourner `ExitCode.INTERRUPTED`.
- [ ] **3. Adapter `src/pyingestkit/cli/main.py`** :
  - [ ] Déléguer l'exécution à `from pyingestkit.cli.bootstrap import main`.
- [ ] **4. Rédiger les tests unitaires sous `tests/unit/cli/`** :
  - [ ] Valider chaque valeur de `ExitCode`.
  - [ ] Mocker `importlib.util.find_spec` pour simuler l'absence de `typer` et vérifier la sortie stdout/stderr et le code de retour 11.
- [ ] **5. Vérifier la non-régression globale** :
  - [ ] Exécuter `make test-v2`.

---

## 4. Preuves & Commandes de Validation

```bash
# Tests unitaires de la CLI
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/ -v

# Vérification du comportement en l'absence de dépendance CLI
PATH="/opt/miniconda3/bin:$PATH" python -c "from pyingestkit.cli.bootstrap import main; sys.exit(main())"
```
