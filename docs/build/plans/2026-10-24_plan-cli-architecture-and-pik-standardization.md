# Plan d'Implémentation : Standardisation de la CLI PyIngestKit (Alignement pik, ptk, pwk)

- **Projet** : PyIngestKit
- **Statut** : Prêt pour implémentation
- **Date** : 24 Octobre 2026
- **Auteur** : Antigravity / Pair Programming
- **Document source** : [`../../analyses/2026-10-24_cli-architecture-patterns-analysis.md`](../../analyses/2026-10-24_cli-architecture-patterns-analysis.md)
- **Références amont** : [`../../../pytransformkit/src/pytransformkit/cli`](../../../pytransformkit/src/pytransformkit/cli) & [`../../../pyworkflowkit/src/pyworkflowkit/cli`](../../../pyworkflowkit/src/pyworkflowkit/cli)
- **Branche cible** : `feat/cli-pik-standardization-and-bootstrap`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation opérationnel vise à hisser l'interface en ligne de commande de **PyIngestKit** au standard architectural unifié du monorepo, éprouvé sur `pytransformkit` (`ptk`) et `pyworkflowkit` (`pwk`) :

1. **Intégration de l'alias officiel `pik`** : Enregistrement du point d'entrée console court `pik` aux côtés des alias `pyingest` et `pyingestkit` dans [`pyproject.toml`](../../../pyproject.toml).
2. **Bootstrap léger stdlib (`bootstrap.py`)** : Démarrage sans dépendance lourde, interception élégante des modules manquants et protection contre `BrokenPipeError` (`SIGPIPE`).
3. **Codes de sortie déterministes (`exit_codes.py`)** : Typage strict des retours processus via `ExitCode(IntEnum)` pour orchestrateurs et scripts de test.
4. **Sécurité workspace & masquage des secrets (`security.py`)** : Confinement filesystem strict (anti-traversal) et redaction automatique des credentials dans tous les flux de sortie.
5. **Commande de diagnostic embarquée (`pik doctor`)** : Inspection automatisée de l'environnement, des variables d'environnement et de la disponibilité des extras optionnels.
6. **Double contrat d'affichage TTY / JSON** : Généralisation du mode machine `--json` sur stdout pour l'intégration programmatique avec `jq`, Airflow et Dagster.

---

## 2. Diagramme d'Architecture du Pipeline CLI `pik`

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| ARCHITECTURE D'EXÉCUTION DE LA COMMANDE 'pik'                                                     |
|                                                                                                   |
|  [ Ingestion Terminal : pik inspect customer_job --json ]                                         |
|                             │                                                                     |
|                             ▼                                                                     |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 1 : Bootstrap Isolé (src/pyingestkit/cli/bootstrap.py)                                 |  |
|  | - 100% Python Standard Library (sys, os, importlib.util)                                     |  |
|  | - Vérifie la présence de typer & rich                                                       |  |
|  |   └─> Si manquant : message d'aide + ExitCode.MISSING_OPTIONAL_DEPENDENCY (11) sans traceback|  |
|  | - Capture les signaux Unix : BrokenPipeError / EPIPE -> ExitCode.BROKEN_PIPE (141)          |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                             │ (Validation OK)                                                     |
|                             ▼                                                                     |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 2 : Sécurité & Routage (src/pyingestkit/cli/app.py & security.py)                      |  |
|  | - assert_path_within_workspace : rejette les chemins hors racine                              |  |
|  | - Filtre de redaction regex : masque mots de passe, tokens et URIs sensibles                |  |
|  | - Typer CLI Routing vers la sous-commande cible                                              |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                             │                                                                     |
|                             ▼                                                                     |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Étape 3 : Services CLI & Core Domain (src/pyingestkit/cli/services/)                         |  |
|  | - InspectionService / DoctorService / JobRunnerService                                      |  |
|  | - IngestionRuntime.run(...)                                                                  |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                             │                                                                     |
|             ┌───────────────┴───────────────┐                                                     |
|             ▼                               ▼                                                     |
|  [ Mode TTY : Rich ]              [ Mode Machine : --json ]                                       |
|  - Tableaux bordés colorés        - JSON pur sur stdout (validé par contrat)                     |
|  - Couleurs HSL officielles       - Logs & avertissements isolés sur stderr                       |
|  - ExitCode typé                  - ExitCode typé                                                 |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
src/pyingestkit/cli/
├── bootstrap.py                        # [CRÉATION] Point d'entrée léger stdlib (guard typer/rich, pipes)
├── exit_codes.py                       # [CRÉATION] Enumération stable des codes de sortie processus
├── security.py                         # [CRÉATION] Anti path-traversal et redaction des secrets
├── commands/
│   └── doctor.py                       # [CRÉATION] Commande 'pik doctor' de diagnostic système
├── app.py                              # [MODIFICATION] Enregistrement de doctor et gestion du nom 'pik'
└── main.py                             # [MODIFICATION] Redirection vers bootstrap.main

pyproject.toml                          # [MODIFICATION] Ajout de [project.scripts] et extra cli
tests/unit/cli/
├── test_bootstrap.py                   # [CRÉATION] Tests du guard stdlib et des dépendances manquantes
├── test_exit_codes.py                  # [CRÉATION] Validation de l'intégrité des codes de sortie
└── test_security.py                    # [CRÉATION] Tests de confinement workspace et redaction secrets
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Socle Résilient : Bootstrap & Exit Codes
**Fichiers à créer :**  
- [`src/pyingestkit/cli/exit_codes.py`](../../../src/pyingestkit/cli/exit_codes.py)  
- [`src/pyingestkit/cli/bootstrap.py`](../../../src/pyingestkit/cli/bootstrap.py)

#### 1. Codes de sortie standardisés (`exit_codes.py`)
```python
"""Stable process exit codes for the PyIngestKit CLI."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes defined by the CLI v1 candidate contract."""

    SUCCESS = 0                      # Exécution nominale
    GENERAL_ERROR = 1                # Erreur d'arguments ou syntaxe
    VALIDATION_ERROR = 2             # Échec de validation (configuration, job, schéma)
    EXECUTION_FAILURE = 3            # Échec d'exécution du job d'ingestion
    SECURITY_ERROR = 4               # Violation de sécurité (path traversal, token leak)
    MISSING_OPTIONAL_DEPENDENCY = 11 # Extra manquant (postgres, s3, cli)
    FILESYSTEM_ERROR = 12            # Fichier introuvable ou droits insuffisants
    INTERNAL_ERROR = 70              # Exception non gérée (bug interne)
    INTERRUPTED = 130                # SIGINT (Ctrl+C standard Unix)
    BROKEN_PIPE = 141                # SIGPIPE (Broken pipe standard Unix)


__all__ = ["ExitCode"]
```

#### 2. Bootstrap stdlib pur (`bootstrap.py`)
```python
"""Dependency-light bootstrap for the PyIngestKit CLI."""

from __future__ import annotations

import errno
import importlib.util
import sys
from collections.abc import Sequence

from pyingestkit.cli.exit_codes import ExitCode

CLI_DEPENDENCIES = ("typer", "rich")
MISSING_DEPENDENCY_EXIT_CODE = int(ExitCode.MISSING_OPTIONAL_DEPENDENCY)


def _missing_cli_dependencies() -> tuple[str, ...]:
    """Return CLI dependencies that are not importable."""
    return tuple(dep for dep in CLI_DEPENDENCIES if importlib.util.find_spec(dep) is None)


def _render_missing_dependency_message(missing: Sequence[str]) -> str:
    """Build a stdlib-only installation hint."""
    return (
        "PyIngestKit CLI dependencies are not installed.\n"
        f"Missing: {', '.join(missing)}\n\n"
        "Install the CLI extra with:\n"
        '  pip install "pyingestkit[cli]"\n'
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run pik while keeping optional CLI imports guarded behind stdlib."""
    missing = _missing_cli_dependencies()
    if missing:
        print(_render_missing_dependency_message(missing), file=sys.stderr)
        return MISSING_DEPENDENCY_EXIT_CODE

    from pyingestkit.cli.app import app

    args = list(argv) if argv is not None else None
    try:
        app(args=args, prog_name="pik", standalone_mode=True)
    except BrokenPipeError:
        return int(ExitCode.BROKEN_PIPE)
    except OSError as exc:
        if exc.errno == errno.EPIPE:
            return int(ExitCode.BROKEN_PIPE)
        raise
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 1
    return 0


__all__ = ["main"]
```

---

### Phase 2 — Sécurité Filesystem & Redaction des Secrets
**Fichier à créer :** [`src/pyingestkit/cli/security.py`](../../../src/pyingestkit/cli/security.py)

```python
"""Filesystem and diagnostic security helpers for PyIngestKit CLI."""

from __future__ import annotations

import re
from pathlib import Path
from pyingestkit.cli.exit_codes import ExitCode

REDACTED = "[REDACTED]"

_SENSITIVE_NAME = (
    r"(?:password|passwd|token|secret|api[_-]?key|"
    r"credential|private[_-]?key|client[_-]?secret)"
)
_URI_USERINFO_PASSWORD_PATTERN = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)([^:@/\s]+):([^/@\s]+)@"
)
_ASSIGNMENT_PATTERN = re.compile(
    rf"""(?ix)
    (
        ["']?{_SENSITIVE_NAME}["']?
        \s*[:=]\s*
    )
    (
        "(?:\\.|[^"])*"
        |
        '(?:\\.|[^'])*'
        |
        [^\s,;]+
    )
    """
)


class SecurityError(RuntimeError):
    """Raised when a security invariant or path boundary is violated."""

    def __init__(self, message: str, exit_code: ExitCode = ExitCode.SECURITY_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def sanitize_input_path(raw_path: str | Path) -> Path:
    """Validate and sanitize an input path string, rejecting null bytes."""
    path_str = str(raw_path)
    if "\0" in path_str:
        raise SecurityError("Path contains prohibited null-byte character.")
    return Path(path_str)


def assert_path_within_workspace(
    path: str | Path,
    workspace_root: str | Path | None = None,
) -> Path:
    """Resolve canonical path and assert it is strictly within allowed workspace."""
    root = (Path(workspace_root) if workspace_root else Path.cwd()).resolve()
    candidate = (root / Path(path)).resolve() if not Path(path).is_absolute() else Path(path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise SecurityError(
            f"Path '{candidate}' escapes the workspace root '{root}'. Access forbidden."
        )
    return candidate


def redact_sensitive_text(text: str) -> str:
    """Mask credentials, passwords, and API keys from CLI output."""
    redacted = _URI_USERINFO_PASSWORD_PATTERN.sub(rf"\1\2:{REDACTED}@", text)
    return _ASSIGNMENT_PATTERN.sub(rf"\1{REDACTED}", redacted)
```

---

### Phase 3 — Enregistrement des Console Scripts dans `pyproject.toml`
**Fichier à modifier :** [`pyproject.toml`](../../../pyproject.toml)

```toml
[project.scripts]
pik = "pyingestkit.cli.bootstrap:main"
pyingest = "pyingestkit.cli.bootstrap:main"
pyingestkit = "pyingestkit.cli.bootstrap:main"

[project.optional-dependencies]
cli = [
  "typer>=0.12,<1",
  "rich>=13,<16",
]
```

---

### Phase 4 — Commande de Diagnostic Système : `pik doctor`
**Fichier à créer :** [`src/pyingestkit/cli/commands/doctor.py`](../../../src/pyingestkit/cli/commands/doctor.py)

La commande `doctor` valide l'environnement et produit soit une vue Rich soit une vue JSON :
```bash
pik doctor
pik doctor --json
```

Informations vérifiées :
1. Version Python et compatibilité (>=3.11).
2. Présence et version du package `pyingestkit`.
3. État des extras installés :
   - `cli` (`typer`, `rich`)
   - `postgres` (`SQLAlchemy`, `psycopg`)
   - `s3` (`boto3`)
   - `http` (`httpx`)
   - `parquet` (`pyarrow`)
4. Résolution de la configuration et des profils `.env`.

---

### Phase 5 — Harmonisation du Mode Machine (`--json`)
**Fichiers à vérifier :** [`src/pyingestkit/cli/commands/*.py`](../../../src/pyingestkit/cli/commands)

Chaque commande exposant des données structurées intègre l'option :
```python
@app.command("inspect")
def inspect_command(
    job_name: str,
    json_output: bool = typer.Option(False, "--json", help="Emit raw JSON machine contract to stdout."),
) -> None:
    ...
```
- Si `json_output=True` : sortie JSON pure sur `sys.stdout`, sans formatage Rich, et logs redirigés sur `sys.stderr`.
- Si `json_output=False` : affichage des tables Rich aux couleurs officielles de la marque.

---

### Phase 6 — Tests Unitaires & Barrières de Qualité
**Fichiers à créer :**
- `tests/unit/cli/test_bootstrap.py` : test d'isolation sans `typer` (mock `find_spec`), test du BrokenPipe.
- `tests/unit/cli/test_exit_codes.py` : test de la stabilité des valeurs entières des codes d'erreur.
- `tests/unit/cli/test_security.py` : tests d'évasion `../../` et masquage des URIs `postgresql://user:pass@host`.

---

## 5. Matrice de Risques & Contrôles

| Risque identifié | Probabilité | Impact | Mesure de mitigation |
| :--- | :--- | :--- | :--- |
| **Conflit de noms de commande console** | Très faible | Faible | `pik`, `pyingest` et `pyingestkit` pointent sur le même entrypoint |
| **Dépendance Typer fuyant dans le package de base** | Très faible | Élevé | Import isolé strictement dans `bootstrap.py` après contrôle `find_spec` |
| **Crash SIGPIPE dans les scripts bash** | Moyen | Moyen | Interception systématique de `BrokenPipeError` et `errno.EPIPE` |
| **Fuite de mot de passe dans les erreurs de connexion** | Faible | Critique | Passage obligatoire des sorties d'erreur par `redact_sensitive_text` |

---

## 6. Critères d'Acceptation & Validation

- [ ] Les commandes `pik --help`, `pyingest --help` et `pyingestkit --help` s'exécutent de façon identique.
- [ ] En l'absence de `typer` / `rich`, `pik` renvoie le code `11` et un message clair sans aucun traceback Python.
- [ ] La commande `pik doctor` dresse un bilan complet et exact des extras installés.
- [ ] La commande `pik doctor --json | jq .` fonctionne immédiatement sans erreur de parsing JSON.
- [ ] Les tentatives d'accès à des fichiers hors workspace échouent avec `ExitCode.SECURITY_ERROR` (code 4).
- [ ] Les tests `make check-v2` et `make quality` restent 100% verts.
