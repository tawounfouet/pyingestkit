# Analyse des Patterns de CLI : Benchmark ptk / pwk et Standard Monorepo pour pik

- **Date :** 24 Octobre 2026  
- **Auteur :** Antigravity / Pair Programming  
- **Packages de référence :**  
  - [`pytransformkit` (CLI `ptk`)](../../../pytransformkit/src/pytransformkit/cli)  
  - [`pyworkflowkit` (CLI `pwk`)](../../../pyworkflowkit/src/pyworkflowkit/cli)  
- **Package cible :** [`pyingestkit` (CLI `pik` / `pyingest`)](../../src/pyingestkit/cli)  
- **Statut :** Spécification de standardisation pour l'ensemble des bibliothèques data du monorepo

---

## 1. Contexte & Vision

Les packages data du monorepo ([`pytransformkit`](../../../pytransformkit), [`pyworkflowkit`](../../../pyworkflowkit), [`pyingestkit`](../../README.md)) partagent un besoin commun : **offrir aux data engineers et orchestrateurs une interface en ligne de commande (CLI) à la fois ergonomique pour l'humain et déterministe pour les machines**.

En examinant `pytransformkit` (`ptk`) et `pyworkflowkit` (`pwk`), on constate l'émergence d'une **architecture de CLI industrielle standardisée**, modulaire et résiliente. 

À l'inverse, dans PyIngestKit, la CLI historique `pyingest` avait été débranchée de `pyproject.toml` en V2 pour alléger les dépendances de base, et l'alias officiel **`pik`** (acronyme de la marque) n'y est pas encore implémenté.

Ce document analyse les 7 patterns d'excellence de `ptk` et `pwk`, et formalise le **standard d'architecture CLI du monorepo** transposable à `pik` et aux futurs packages.

---

## 2. Le Standard Architectural des CLI du Monorepo

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| ARCHITECTURE STANDARDISÉE D'UNE CLI DANS LE MONOREPO                                             |
|                                                                                                   |
|  [ Terminal / Shell : Invocation de 'ptk', 'pwk' ou 'pik' ]                                       |
|                                │                                                                  |
|                                ▼                                                                  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Couche 1 : Bootstrap Isolé & Léger (bootstrap.py)                                           |  |
|  | - 100% Python Standard Library (zéro dépendance lourde au démarrage)                         |  |
|  | - Détection élégante des extras manquants (typer, rich) avec message d'installation propre  |  |
|  | - Gestion native des flux Unix : SIGINT (130) et SIGPIPE (EPIPE / 141)                      |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                                │ (Dépendances validées)                                           |
|                                ▼                                                                  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Couche 2 : Sécurité & Routage (app.py + security.py)                                        |  |
|  | - Anti Path-Traversal (assert_path_within_workspace)                                         |  |
|  | - Redaction automatique des secrets et URIs sensibles (credentials, tokens, password)       |  |
|  | - Typer Command Routing & Flag Parsing                                                      |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                                │                                                                  |
|                                ▼                                                                  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Couche 3 : Services Applicatifs de la CLI (services/)                                        |  |
|  | - Orchestration spécifique à la CLI : Inspection, Exécution, Diagnostics                     |  |
|  | - ZÉRO logique de routing Typer ou d'affichage dans cette couche                           |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                                │                                                                  |
|        ┌───────────────────────┴───────────────────────┐                                          |
|        ▼                                               ▼                                          |
|  [ Mode Humain / TTY ]                           [ Mode Machine (--json) ]                        |
|  - Rendu Rich (tableaux, panels, couleurs)       - JSON pur sur stdout                            |
|  - Messages informatifs sur stderr               - Schéma machine contractuel versionné           |
|  - Codes de sortie typés (exit_codes.py)         - Logs et warnings isolés sur stderr             |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Les 7 Patterns Majeurs Identifiés

### Pattern 1 : Le Bootstrap Léger et Résilient (`bootstrap.py`)
*Exemples : [`pytransformkit/.../bootstrap.py`](../../../pytransformkit/src/pytransformkit/cli/bootstrap.py) et [`pyworkflowkit/.../bootstrap.py`](../../../pyworkflowkit/src/pyworkflowkit/cli/bootstrap.py)*

#### Principe :
Le point d'entrée console ne doit **jamais** importer directement `typer` ou `rich` au niveau du module. Il utilise `importlib.util.find_spec` :
- Si `typer` ou `rich` manque, la commande quitte proprement avec un message pédagogique et un code de sortie dédié, sans afficher de traceback Python `ModuleNotFoundError`.
- Il protège contre `BrokenPipeError` (lorsque la sortie est pipée vers `head` ou `grep` qui se ferment avant la fin du flux).

```python
# Modèle standard du bootstrap.py
CLI_DEPENDENCIES = ("typer", "rich")

def main(argv: Sequence[str] | None = None) -> int:
    missing = tuple(dep for dep in CLI_DEPENDENCIES if importlib.util.find_spec(dep) is None)
    if missing:
        print(f"CLI dependencies missing: {', '.join(missing)}.\n"
              'Install with: pip install "pyingestkit[cli]"', file=sys.stderr)
        return int(ExitCode.MISSING_OPTIONAL_DEPENDENCY)

    from pyingestkit.cli.app import app
    try:
        app(args=list(argv) if argv is not None else None, prog_name="pik", standalone_mode=True)
    except BrokenPipeError:
        return int(ExitCode.BROKEN_PIPE)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0
```

---

### Pattern 2 : Codes de Sortie Processus Stables (`exit_codes.py`)
*Exemples : [`pytransformkit/.../exit_codes.py`](../../../pytransformkit/src/pytransformkit/cli/exit_codes.py) et [`pyworkflowkit/.../exit_codes.py`](../../../pyworkflowkit/src/pyworkflowkit/cli/exit_codes.py)*

#### Principe :
Au lieu d'utiliser `exit(1)` pour toutes les erreurs, une `IntEnum` stable catégorise les échecs pour permettre aux scripts bash et orchestrateurs d'adopter des stratégies de remédiation ciblées.

```python
class ExitCode(IntEnum):
    SUCCESS = 0                      # Exécution nominale
    GENERAL_ERROR = 1                # Erreur d'arguments ou syntaxe
    VALIDATION_ERROR = 2             # Échec de validation (schéma, contrat, DAG)
    EXECUTION_FAILURE = 3            # Échec d'exécution du job/workflow
    SECURITY_ERROR = 4               # Violation de sécurité (path traversal, token leak)
    MISSING_OPTIONAL_DEPENDENCY = 11 # Extra manquant (postgres, s3, etc.)
    INTERNAL_ERROR = 70              # Exception non gérée (bug interne)
    INTERRUPTED = 130                # SIGINT (Ctrl+C standard Unix)
    BROKEN_PIPE = 141                # SIGPIPE (Broken pipe standard Unix)
```

---

### Pattern 3 : Sécurité Filesystem & Redaction des Secrets (`security.py`)
*Exemples : [`pyworkflowkit/.../security.py`](../../../pyworkflowkit/src/pyworkflowkit/cli/security.py)*

#### Principe :
Les outils CLI de data ingèrent et manipulent des chemins de fichiers et des chaînes de connexion. Deux sécurités sont obligatoires :
1. **Confinement dans le Workspace (`assert_path_within_workspace`)** : Interdit tout chargement de fichier s'échappant de la racine du projet (protection contre `../../../../etc/passwd` ou arguments malicieux).
2. **Redaction automatique des secrets** : Masquage systématique des mots de passe dans les URLs (`postgresql://user:***@host`), tokens d'API, et headers d'authentification avant tout affichage ou log.

```text
+---------------------------------------------------------------------------------------------------+
| PIPELINE DE SÉCURITÉ DES SORTIES CLI                                                             |
|                                                                                                   |
|  Donnée brute ───> [ Filtre Regex Secrets ] ───> [ Contrôle Path Boundary ] ───> Sortie Sécurisée|
|  (URI, Token)       (remplace par [REDACTED])      (rejette hors-workspace)      (Terminal / JSON)|
+---------------------------------------------------------------------------------------------------+
```

---

### Pattern 4 : Double Contrat de Rendu (Humain Rich vs Machine JSON)

#### Principe :
Toute commande produisant des informations ou des rapports (`inspect`, `status`, `config`, `runs`) doit supporter le flag `--json` :
- **Mode Humain (TTY)** : Présentation soignée avec Rich (tableaux, arborescences, couleurs HSL du package, spinners).
- **Mode Machine (`--json`)** : Sortie JSON brute, strictement conforme à un contrat de schéma versionné (`CLI_CONTRACT_VERSION = 1`).
- **Séparation des flux** : En mode `--json`, les éventuels messages de log ou d'avertissement sont redirigés sur `stderr` pour que `stdout` reste un JSON valide, directement exploitable par `jq`.

```bash
# Rendu humain
pik inspect customer_job

# Rendu machine intégrable dans Airflow / Dagster
pik inspect customer_job --json | jq '.dataset_version'
```

---

### Pattern 5 : Diagnostic Système Embarqué (`doctor`)
*Exemples : `ptk doctor` et `pwk doctor`*

#### Principe :
Une commande standard `doctor` teste la viabilité de l'environnement d'exécution local :
- Version exacte de Python et du framework.
- Statut des extras installés (`postgres`, `s3`, `http`).
- Présence des dépendances système (drivers C, connectivité locale).
- Validation des variables d'environnement (`.env` résolu).

---

### Pattern 6 : Découplage Hexagonal de la CLI (`services/`)

#### Principe :
Aucune commande Typer ne doit contenir de logique métier. Les commandes se contentent de :
1. Valider et convertir les arguments CLI.
2. Appeler un service applicatif dédié sous `pyingestkit.cli.services.*`.
3. Passer le résultat au moteur de rendu (Rich ou JSON).

```text
pyingestkit/cli/
├── commands/     <- ty.command() : routing et flags uniquement
├── services/     <- Logique applicative CLI pure (sans typer ni rich)
├── rendering/    <- Formatage des tableaux Rich et sérialiseurs JSON
└── models/       <- DTOs et structures de données de rapport
```

---

### Pattern 7 : Nomenclature Tripartite et Multi-Aliasing
*Exemples : `ptk`, `pwk`, et cible `pik`*

#### Principe :
Pour chaque package data du monorepo, exposer une triple entrée de commande dans `pyproject.toml` :
1. **L'alias court (3 lettres)** : Idéal pour les développeurs au clavier (`pik`, `ptk`, `pwk`).
2. **Le nom fonctionnel classique** : Idéal pour la lisibilité des scripts (`pyingest`, `pyworkflow`).
3. **Le nom complet du package** : Idéal pour l'automatisation sans ambiguïté (`pyingestkit`, `pyworkflowkit`).

```toml
[project.scripts]
pik = "pyingestkit.cli.bootstrap:main"
pyingest = "pyingestkit.cli.bootstrap:main"
pyingestkit = "pyingestkit.cli.bootstrap:main"
```

---

## 4. Comparatif de l'Existant PyIngestKit vs Standard Monorepo

| Composant | État Actuel dans PyIngestKit | Standard Cible Monorepo (`pik`) |
| :--- | :--- | :--- |
| **Point d'entrée `pyproject.toml`** | ❌ Aucun `[project.scripts]` | ✅ `pik`, `pyingest`, `pyingestkit` |
| **Bootstrap Guard** | ❌ Import Typer direct dans `cli/main.py` | ✅ `bootstrap.py` standardisé (stdlib pure) |
| **Gestion des extras** | ❌ Typer dans `dev` uniquement | ✅ Extra optionnel `cli = ["typer", "rich"]` |
| **Codes d'erreur** | ⚠️ Typer exceptions génériques | ✅ `ExitCode(IntEnum)` stable et typé |
| **Sécurité Filesystem** | ⚠️ Validation de path ad-hoc | ✅ `assert_path_within_workspace` |
| **Redaction des secrets** | ⚠️ Redaction interne au ledger | ✅ Redaction appliquée à toute la CLI |
| **Double rendu TTY / JSON** | ⚠️ Présent sur certaines commandes | ✅ Généralisé et contractuel sur toutes |
| **Commande `doctor`** | ❌ Absente | ✅ Diagnostic complet environnement & extras |

---

## 5. Feuille de Route d'Alignement pour PyIngestKit

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| PHASAGE DE LA MISE À NIVEAU CLI DANS PYINGESTKIT                                                  |
|                                                                                                   |
|  Phase 1 : Socle Technique                                                                        |
|  - Création de src/pyingestkit/cli/bootstrap.py (stdlib guard)                                   |
|  - Création de src/pyingestkit/cli/exit_codes.py                                                   |
|  - Déclaration de l'extra cli et de [project.scripts] (pik, pyingest, pyingestkit)                |
|                                                                                                   |
|  Phase 2 : Sécurité & Normalisation                                                               |
|  - Implémentation de cli/security.py (confinement workspace + redaction de secrets)              |
|  - Séparation stricte commands/ vs services/                                                      |
|                                                                                                   |
|  Phase 3 : Commandes Système & Contrats Machine                                                   |
|  - Ajout de la commande pik doctor                                                                |
|  - Harmonisation du flag --json sur toutes les commandes d'inspection                             |
|  - Gel du contrat machine CLI v1 dans tests/contract/fixtures/                                    |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```
