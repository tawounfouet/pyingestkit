# FEEDBACK-LOT31-01 : Retour d'Expérience sur le Bootstrap CLI Stdlib & Codes de Sortie

- **Tâche Évaluée :** [`../tasks/TASK-LOT31-01_cli-bootstrap-and-exit-codes.md`](../tasks/TASK-LOT31-01_cli-bootstrap-and-exit-codes.md)
- **Plan Parent :** [`../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-24
- **Évaluation Globale :** 🟢 Excellente (Bootstrap zéro-dépendance atteint, suite V2 et CLI 100 % au vert)

---

## 1. Résumé de la Session d'Exécution

L'exécution de la tâche `TASK-LOT31-01` a doté PyIngestKit du standard CLI de la suite (`ptk`, `pwk`) :
- Création de `ExitCode(IntEnum)` standardisé dans `src/pyingestkit/cli/exit_codes.py` (0, 1, 2, 3, 4, 11, 12, 70, 130, 141).
- Création du bootstrap stdlib ultra-léger dans `src/pyingestkit/cli/bootstrap.py` avec vérification `find_spec` pour `typer` et `rich`, interception gracieuse de `BrokenPipeError` et `KeyboardInterrupt`, et chargement hiérarchique des profils `.env` (priorité `infra/envs/`).
- Enregistrement des console-scripts `pik`, `pyingest`, `pyingestkit` dans `pyproject.toml`.
- Passage de `app` en lazy import via PEP 562 (`__getattr__`) dans `src/pyingestkit/cli/__init__.py`.
- Validation : 9/9 tests CLI passés, 79/79 architecture V2 passés, 76/76 contrats V2 passés, 367 tests unitaires/intégration passés, ruff + mypy sans aucune erreur.

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Bootstrap stdlib pur :**
   En l'absence de Typer ou Rich, la commande `pik` ne crashe plus avec un `ModuleNotFoundError` opaque, mais affiche un guide d'installation propre (`pip install "pyingestkit[cli]"`) et sort avec le code normalisé `11` (`MISSING_OPTIONAL_DEPENDENCY`).
2. **Support direct de la nouvelle arborescence `infra/envs/` :**
   La fonction `_load_local_dotenv()` inspecte d'abord `infra/envs/.env.<profile>` avant le fallback `envs/`, assurant la cohérence avec le réaménagement `TASK-LOT32-01`.
3. **Double alias de commande :**
   Les utilisateurs et scripts CI peuvent invoquer indifféremment `pik`, `pyingest` ou `pyingestkit`.

---

## 3. Frictions & Points d'Attention Rencontrés

1. **Import eager dans `src/pyingestkit/cli/__init__.py` :**
   Le fichier `__init__.py` contenait initialement `from .app import app`. Dès lors, le simple fait d'importer `pyingestkit.cli.exit_codes` ou `pyingestkit.cli.bootstrap` provoquait l'importation de `app.py`, annulant l'objectif "zéro dépendance lourde au démarrage".
   *Solution :* Remplacement par un `__getattr__` dynamique (PEP 562) différant l'import de `app` au moment de son premier accès effectif.
2. **Corruption du descripteur de fichier pytest par `os.dup2` :**
   La gestion standard Unix du signal `BrokenPipeError` consiste à rediriger le descripteur de stdout vers `/dev/null` (`os.dup2(devnull, sys.stdout.fileno())`) pour éviter les alertes de runtime au shutdown. Cependant, dans le cadre de pytest qui intercepte `sys.stdout` via des pipes temporaires, ce `os.dup2` écrasait le descripteur de capture du test runner, causant une erreur globale `OSError: [Errno 9] Bad file descriptor`.
   *Solution :* Conditionner l'appel à `os.dup2` par l'absence de `PYTEST_CURRENT_TEST` dans les variables d'environnement.
3. **Résolution des types mypy avec `__getattr__` :**
   L'utilisation de `__getattr__` dans les packages de transition (`artifacts`, `replay`, `runtime`) renvoyait un type `object` non reconnu par mypy pour les annotations de classes.
   *Solution :* Ajout de blocs `if TYPE_CHECKING:` avec des alias redondants (`from .s3 import S3ArtifactStore as S3ArtifactStore`) reconnus par Ruff et Mypy.

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

- **Conservation du contrat d'export V2 figé :**
  Les 11 symboles de `src/pyingestkit/__init__.py` et les exports stricts de `artifacts`, `replay`, `runtime` n'ont pas été pollués. La rétrocompatibilité avec les sous-modules historiques a été assurée exclusivement via PEP 562 `__getattr__` et `TYPE_CHECKING`.
- **Alignement des codes d'erreur sur la suite WebTech :**
  Le code de sortie `11` est harmonisé avec `ptk` pour signaler une dépendance manquante, et `141` pour le comportement Unix standard face à un Broken Pipe.

---

## 5. Actions d'Amélioration Immédiates (Feedback Loop)

- [x] **Généraliser PEP 562 `__getattr__` :** Utiliser systématiquement ce pattern pour tout point d'entrée CLI ou sous-package afin d'éviter les imports circulaires ou prématurés.
- [x] **Protéger tout `os.dup2` en contexte de test :** Ne jamais écraser les descripteurs 1 et 2 lorsque `PYTEST_CURRENT_TEST` est défini.
- [x] **Prochaine étape (LOT-31) :** Passer à `TASK-LOT31-02` (Sécurité & Redaction des credentials dans les commandes et logs CLI).
