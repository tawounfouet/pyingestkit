# PyIngestKit — Stabilisation de la Foundation V0.1.x avant V0.2

**Document de référence d’architecture et de stabilisation**  
**Projet :** PyIngestKit  
**Périmètre :** Foundation V0.1.x  
**Cible de consolidation :** V0.1.6 — Foundation Persistence & Quality Hardening  
**Étape suivante autorisée :** V0.2 — Acquisition & Dataset Contracts  
**Date :** 2026-09-03  
**Statut :** V0.1.5 implémentée et validée fonctionnellement ; V0.1.6 obligatoire pour rendre tous les gates qualité/sécurité verts avant V0.2

---

## 0. Résumé exécutif

PyIngestKit a désormais franchi deux étapes distinctes de sa Foundation :

- **V0.1.4** : CLI Typer/Rich, configuration YAML/Pydantic, logging Rich + JSON, plugin pack installable ;
- **V0.1.5** : consolidation fonctionnelle du runtime avec workspace unique, `MetadataStore`, SQLite par défaut, historique des runs, events persistés, API déclarative `@job` / `@step`, RAW immuable, manifest enrichi et CLI `runs/status`.

Les essais réels de la V0.1.5 confirment que la Foundation est **fonctionnellement cohérente** :

```text
un seul workspace .pyingest/
SQLite alimenté
runs / steps / artifacts / events persistés
logs terminal Rich timestampés
logs JSON structurés
plugin déclaratif découvert via entry point
manifest relié au RAW
CLI runs / status opérationnelle
55 tests pytest verts
54 tests unittest verts
build wheel/sdist réussi
```

Cependant, les quality/security gates exécutés localement ont révélé que la Foundation n’est **pas encore entièrement green** :

```text
Ruff          → 56 erreurs
Bandit        → 4 findings B608 Medium/Medium
Mypy strict   → non atteint tant que Ruff bloque make quality
pip-audit     → non atteint tant que Bandit bloque make security
Packaging     → build OK mais warnings PEP 639 / license metadata
```

La V0.1.5 doit donc être considérée comme :

> **fonctionnellement consolidée, mais pas encore gelée comme Foundation production-grade.**

La dernière étape avant V0.2 devient une **V0.1.6 — Foundation Persistence & Quality Hardening**, sans nouvelle capacité d’ingestion métier. Son rôle est de :

1. intégrer **SQLAlchemy 2.x** comme moteur interne de persistence metadata ;
2. supprimer la duplication SQL manuelle SQLite/PostgreSQL ;
3. conserver `MetadataStore` comme contrat public et empêcher toute fuite ORM dans le core ;
4. garder SQLite comme backend local par défaut ;
5. garder PostgreSQL comme backend interchangeable via adapter + `psycopg` optionnel ;
6. éliminer les constructions SQL dynamiques signalées par Bandit ;
7. rendre **Ruff, Ruff format, Mypy strict, Bandit et pip-audit réellement verts** ;
8. moderniser le packaging PEP 639 ;
9. introduire un gate agrégé `make verify` dont l’exit code `0` devient la condition d’ouverture de V0.2 ;
10. conserver tous les garde-fous de scope : pas de scheduler, pas de DAG distribué, pas de Data Platform, pas de second ORM, pas d’Alembic prématuré.

La trajectoire finale devient :

```text
V0.1.4
────────────────────────────────
CLI Typer/Rich
Configuration YAML/Pydantic
Plugins
RAW / Manifest
Logging Rich + JSON

                ↓

V0.1.5 — IMPLEMENTED
FOUNDATION CONSOLIDATION
────────────────────────────────
Workspace unifié
MetadataStore
SQLite par défaut
PostgreSQL adapter contract
Runs / steps / artifacts / events persistés
Logging terminal stabilisé
-v / -q
CLI runs / status
Decorator API @job / @step
Builder déclaratif → modèle impératif
RAW immuable
Manifest enrichi
Plugin isolation

                ↓

V0.1.6 — REQUIRED BEFORE V0.2
PERSISTENCE & QUALITY HARDENING
────────────────────────────────
SQLAlchemy 2.x Core
Persistence repository commun
SQLite adapter SQLAlchemy
PostgreSQL adapter SQLAlchemy + psycopg extra
Ruff 0
Ruff format green
Mypy strict green
Bandit 0 findings
pip-audit green
PEP 639 packaging clean
make verify = 0
wheel smoke tests green

                ↓

V0.2
INGESTION CAPABILITIES
────────────────────────────────
HTTP
Retry
CSV
JSON
Dataset Contracts
```

# 1. Vision rappelée

## 1.1 Thèse centrale de PyIngestKit

PyIngestKit doit permettre de :

> **Transformer une source externe en dataset fiable, traçable, validé, reproductible et publiable sans réécrire la plomberie technique dans chaque job.**

Le cycle de vie de référence reste :

```text
DISCOVER
   ↓
FETCH
   ↓
RAW
   ↓
HASH / PROVENANCE
   ↓
PARSE
   ↓
NORMALIZE
   ↓
VALIDATE
   ↓
CROSS-CHECK
   ↓
DIFF
   ↓
PUBLISH
   ↓
LOAD
   ↓
MANIFEST / METRICS / RUN STATUS
```

La Foundation V0.1.x ne doit pas implémenter tout ce cycle immédiatement, mais elle doit offrir des contrats suffisamment solides pour que les briques suivantes s’y branchent sans remise en cause majeure du runtime.

---

# 2. Frontière produit à préserver

PyIngestKit est un framework d’ingestion batch composable.

Il fournit :

- des contrats `Job`, `Step`, `Pipeline`, `RunContext`, `RunResult` ;
- un runtime d’exécution ;
- des primitives de sources ;
- un cycle de vie d’artefacts ;
- de la provenance et du hashing ;
- de la validation ;
- de la publication ;
- des targets ;
- un système de plugins ;
- des métadonnées de run ;
- une CLI ;
- des conventions de configuration, logging et observabilité.

Il **ne doit pas devenir** :

- Airflow ;
- Dagster ;
- Prefect ;
- Celery ;
- un scheduler distribué ;
- un cluster manager ;
- un moteur Kubernetes ;
- un orchestrateur de workflows généraliste ;
- un ETL visuel ;
- une Data Platform ;
- un Data Catalog ;
- un système IAM/RBAC ;
- une plateforme AI/Agents/RAG ;
- une application SaaS/web ;
- un framework universel d’intégration.

La doctrine reste :

```text
Orchestrator externe
      ↓
QUAND exécuter

PyIngestKit
      ↓
COMMENT ingérer
```

---

# 3. Test d’admission d’une nouvelle feature

Avant d’ajouter une capacité au cœur de PyIngestKit, répondre à ces questions :

1. Est-elle utile à plusieurs types de jobs d’ingestion ?
2. Est-elle indépendante du domaine métier ?
3. Est-elle directement liée au lifecycle d’ingestion ?
4. Évite-t-elle de transformer PyIngestKit en orchestrateur ou plateforme ?
5. Réduit-elle réellement la duplication inter-projets ?

Si plusieurs réponses sont **NON**, la feature doit probablement être :

- un plugin ;
- un package externe ;
- une responsabilité du job métier ;
- une responsabilité de l’orchestrateur ;
- ou ne pas être développée.

---

# 4. Leçons des projets précédents

La trajectoire historique reste utile pour garder la discipline :

```text
python-connectors
→ NE PAS DUPLIQUER

PyConnectors
→ CONSTRUIRE DES CONTRATS

PyWorkflow Engine
→ POSER DES FRONTIÈRES

PyIngestKit
→ FACTORISER + CONTRACTUALISER + RESTER ÉTROIT
```

Le principal garde-fou hérité de PyWorkflow Engine est le suivant :

> Une bonne architecture n’est pas seulement celle qui sait accueillir beaucoup de fonctionnalités ; c’est aussi celle qui sait explicitement dire NON.

---

# 5. État réel atteint en V0.1.5

La V0.1.5 n’est plus une simple cible : elle a été implémentée et testée sur un environnement local réel.

## 5.1 Core / Runtime

Disponibles et validés :

- `Job` ;
- `Step` ;
- `Pipeline` ;
- `RunContext` ;
- `StepResult` ;
- `RunResult` ;
- `RunStatus` ;
- `JobRegistry` ;
- `EventBus` ;
- `Runner` ;
- hooks best-effort / critical ;
- persistence des runs réussis et échoués ;
- persistence des steps ;
- persistence des événements structurants ;
- lifecycle cohérent même lors de plusieurs scénarios d’échec testés.

## 5.2 Artefacts / provenance

Disponibles et validés :

- `LocalArtifactStore` ;
- layout de run ;
- `RawArtifact` ;
- SHA-256 ;
- RAW immuable dans un même run ;
- `RunManifest` ;
- artefacts RAW automatiquement référencés dans le manifest ;
- artefacts RAW automatiquement référencés dans le `MetadataStore` ;
- écriture JSON atomique ;
- publication atomique via remplacement de fichier.

## 5.3 Workspace

Le workspace est désormais unifié :

```text
.pyingest/
├── logs/
│   └── pyingest.log
├── runs/
│   └── <namespace>/<job>/<run_id>/...
└── state/
    └── pyingest.sqlite3
```

Le précédent `.pyingest-demo/` n’est plus créé par défaut.

## 5.4 Sources

Disponible :

- `LocalSource`.

Les sources HTTP appartiennent à V0.2.

## 5.5 Validation / Publication

Disponibles :

- `ValidationSeverity` ;
- `ValidationIssue` ;
- `ValidationReport` ;
- `ValidationRule` ;
- `MinimumRows` ;
- `RequiredField` ;
- `UniqueField` ;
- infrastructure `MetadataStore` prête pour validations et publications.

Les tables `validations` et `publications` peuvent être vides pour un job qui ne déclenche aucun lifecycle de validation/publication : ce comportement est normal.

## 5.6 Configuration

Disponibles :

- `PyYAML` ;
- `Pydantic` ;
- validation stricte `extra="forbid"` ;
- `pyingest.yml` ;
- configuration runtime ;
- configuration metadata ;
- configuration logging ;
- précédence claire.

Ordre de précédence :

```text
Framework defaults
        ↓
pyingest.yml
        ↓
--params-json
        ↓
--param / -p
        ↓
options CLI explicites
```

## 5.7 CLI

La CLI repose sur Typer + Rich et expose :

```text
pyingest jobs
pyingest inspect
pyingest run
pyingest runs
pyingest status
pyingest help
```

Support :

```text
--json
-v / --verbose
-q / --quiet
--log-level
```

Les logs utilisent `stderr` et les payloads `--json` utilisent `stdout`, ce qui permet la redirection machine-safe même si le terminal affiche les deux flux lorsqu’ils ne sont pas redirigés.

## 5.8 Plugins

Découverte via :

```toml
[project.entry-points."pyingestkit.jobs"]
```

Le package démo installable démontre :

```text
plugin install
   ↓
entry point discovery
   ↓
pyingest jobs
   ↓
pyingest inspect
   ↓
pyingest run
```

Les plugins cassés sont isolés afin qu’un plugin tiers défectueux ne masque pas les plugins sains.

## 5.9 Declarative API

La V0.1.5 expose :

- `@step` ;
- `@job` ;
- `StepDefinition` ;
- `StepInvocation` ;
- `JobDefinition` ;
- `PipelineBuilder` ;
- compilation vers le même modèle impératif ;
- surface `.fn()` pour tests unitaires directs.

La Decorator API devient la DX recommandée ; l’API impérative reste le modèle bas niveau stable.

## 5.10 Logging

Le logging repose sur :

```text
Python logging
      +
Rich terminal rendering
      +
JSON rotating file logging
```

Format terminal figé :

```text
2026-09-03 19:03:31  INFO     [run=f0dcc144 job=demo.local_file] Run started
2026-09-03 19:03:31  INFO     [run=f0dcc144 job=demo.local_file step=FetchLocal] Step started
2026-09-03 19:03:31  INFO     [run=f0dcc144 job=demo.local_file step=FetchLocal] Step succeeded 0.006s
2026-09-03 19:03:31  INFO     [run=f0dcc144 job=demo.local_file] Run succeeded 0.024s
```

Les fichiers JSON conservent l’UUID complet et un timestamp ISO 8601 timezone-aware.

## 5.11 Persistance réelle observée

SQLite contient déjà les tables :

```text
runs
steps
artifacts
events
validations
publications
```

Les commandes `pyingest runs` et `pyingest status` interrogent ces métadonnées.

## 5.12 Validation fonctionnelle V0.1.5

État mesuré :

```text
pytest                 55 passed
unittest               54 passed
public API contract    OK
compileall             OK
wheel/sdist build      OK
plugin wheel build     OK
CLI smoke              OK
SQLite persistence     OK
```

Cet état ne doit pas être confondu avec un état “quality gates green” : ce dernier est précisément l’objectif V0.1.6.

# 6. Politique de dépendances

La contrainte historique `zero third-party dependency` est abandonnée.

La doctrine devient :

> PyIngestKit utilise des dépendances tierces reconnues lorsqu’elles réduisent la complexité réelle et améliorent robustesse, maintenabilité, sécurité, typage, DX ou industrialisation.

Dépendances de socle retenues :

- `Typer` — CLI ;
- `Rich` — rendu terminal ;
- `Pydantic` — configuration typée/validée ;
- `PyYAML` — configuration YAML ;
- **`SQLAlchemy 2.x` — persistence metadata multi-backend à partir de V0.1.6**.

Dépendance optionnelle prévue :

- `psycopg` via extra `[postgres]` pour PostgreSQL.

Le principe n’est pas :

```text
minimum de dépendances à tout prix
```

mais :

```text
dépendances utiles
+ explicites
+ maintenues
+ auditées
+ bornées
+ avec une responsabilité claire
```

Garde-fous :

- pas de dépendance ajoutée sans cas d’usage précis ;
- pas de duplication d’une capacité mature existante ;
- versions bornées raisonnablement ;
- `pip-audit` obligatoire dans le gate sécurité ;
- changelog des changements de dépendances structurants ;
- extras uniquement lorsque la dépendance est réellement optionnelle ;
- **un seul moteur de persistence interne : SQLAlchemy** ;
- **Peewee n’est pas ajouté** : deux ORMs concurrents n’apporteraient aucune valeur ;
- SQLAlchemy reste un détail interne de persistence et ne fuit pas dans le core ou l’API utilisateur.

# 7. Ajustement n°1 — Workspace unique

## 7.1 Problème actuel

Les tests et exemples ont fait apparaître :

```text
.pyingest/
.pyingest-demo/
```

Les deux contiennent presque la même structure car ils exécutent le même runtime avec des workspaces différents.

La séparation `.pyingest-demo/` n’apporte pas de vraie valeur par défaut.

## 7.2 Décision cible

Unifier sur :

```text
.pyingest/
├── runs/
├── logs/
├── state/
└── published/
```

L’isolation des jobs se fait par namespace :

```text
.pyingest/runs/
└── demo/
    └── local_file/
        └── <run_id>/
```

Le plugin démo doit donc utiliser :

```yaml
runtime:
  workspace: .pyingest
```

Un autre workspace reste possible explicitement :

```bash
pyingest run demo.local_file --workspace .pyingest-demo
```

mais ce n’est plus le comportement par défaut.

## 7.3 Layout cible

```text
.pyingest/
│
├── state/
│   └── pyingest.sqlite3
│
├── logs/
│   └── pyingest.log
│
├── runs/
│   └── <namespace>/
│       └── <job>/
│           └── <run_id>/
│               ├── raw/
│               ├── staging/
│               ├── candidate/
│               ├── reports/
│               └── manifest.json
│
└── published/
    └── <namespace>/
        └── <dataset>/
            ├── current/
            └── history/
```

Garde-fou : **un plugin ne choisit pas silencieusement un autre workspace global**.

---

# 8. Ajustement n°2 — Séparer ArtifactStore et MetadataStore

## 8.1 Principe

Le filesystem est adapté aux fichiers et artefacts lourds.

Il est moins adapté pour interroger l’historique des exécutions.

Il faut donc distinguer :

```text
ArtifactStore
→ données / fichiers / artefacts

MetadataStore
→ état structuré du runtime
```

Architecture cible :

```text
                       PyIngestKit
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
     ArtifactStore                      MetadataStore
           │                                 │
      fichiers lourds                   état structuré
           │                                 │
      RAW                                Runs
      reports                            Steps
      manifests                          Artifacts metadata
      datasets                           Validations
                                         Publications
                                         Events
```

## 8.2 ArtifactStore conserve

- RAW ;
- staging ;
- candidate ;
- reports ;
- manifest ;
- datasets publiés ;
- fichiers de diff ;
- snapshots éventuels.

## 8.3 MetadataStore conserve

- runs ;
- steps ;
- statut ;
- durée ;
- erreurs ;
- paramètres ;
- métadonnées d’artefacts ;
- validations ;
- publications ;
- événements runtime structurants.

Garde-fou : **ne pas stocker les gros artefacts binaires dans MetadataStore**.

---

# 9. Ajustement n°3 — SQLite comme MetadataStore par défaut

## 9.1 Pourquoi SQLite

SQLite est particulièrement pertinent pour :

- workstation développeur ;
- CLI locale ;
- jobs cron simples ;
- CI ;
- GitHub Actions ;
- serveur unique ;
- tests ;
- environnement offline ;
- déploiement sans service externe.

Avantages :

- aucune infrastructure à déployer ;
- transactions ;
- indexes ;
- SQL ;
- requêtes historiques ;
- portabilité ;
- backup simple ;
- fichier unique.

## 9.2 Abstraction cible

```text
metadata/
├── base.py
├── models.py
├── sqlalchemy/
│   ├── schema.py
│   ├── repository.py
│   └── engine.py
├── sqlite.py
└── postgres.py
```

Contrat conceptuel :

```python
class MetadataStore(Protocol):
    def create_run(...): ...
    def update_run(...): ...
    def record_step(...): ...
    def record_artifact(...): ...
    def record_validation(...): ...
    def record_publication(...): ...
    def record_event(...): ...
    def get_run(...): ...
    def list_runs(...): ...
```

Le `Runner` ne doit jamais connaître SQLite directement.

Il doit uniquement dépendre du contrat `MetadataStore`.

---

# 10. Schéma SQLite V0.1.x recommandé

Le schéma doit rester minimal.

## 10.1 Table `run`

```text
run
────────────────────────────────────
run_id               PK
job_id
job_version
status
started_at
completed_at
duration_seconds
fixture_mode
parameters_json
error
created_at
```

## 10.2 Table `step`

```text
step
────────────────────────────────────
id                   PK
run_id               FK
step_name
position
status
started_at
completed_at
duration_seconds
error
metrics_json
```

## 10.3 Table `artifact`

```text
artifact
────────────────────────────────────
artifact_id          PK
run_id               FK
kind
path
source_uri
content_type
size_bytes
sha256
created_at
```

## 10.4 Table `validation`

```text
validation
────────────────────────────────────
id
run_id
rule
severity
status
message
metadata_json
```

## 10.5 Table `publication`

```text
publication
────────────────────────────────────
id
run_id
dataset_id
status
candidate_path
published_path
published_at
```

## 10.6 Table `event`

```text
event
────────────────────────────────────
id
run_id
job_id
step
event_type
level
message
created_at
metadata_json
```

Garde-fou : ne pas sur-normaliser trop tôt le schéma ; la V0.1.x doit couvrir les requêtes runtime essentielles, pas devenir un entrepôt analytique.

---

# 11. Ajustement n°4 — SQLAlchemy 2.x derrière les adapters SQLite/PostgreSQL

## 11.1 Décision

À partir de V0.1.6, PyIngestKit doit remplacer le SQL manuel des `MetadataStore` par **SQLAlchemy 2.x**, en privilégiant **SQLAlchemy Core** pour la Foundation.

La décision n’est pas d’exposer un ORM aux auteurs de jobs. La décision est de disposer d’un moteur de persistence interne mature et portable.

Architecture :

```text
Runner / CLI
     │
     ▼
MetadataStore
     │
     ▼
SQLAlchemy persistence layer
     │
 ┌───┴───────────────┐
 ▼                   ▼
SQLite              PostgreSQL
stdlib sqlite3      psycopg extra
```

## 11.2 Pourquoi SQLAlchemy maintenant

Le moment est approprié car :

- la persistence metadata vient juste d’être introduite ;
- le contrat public `MetadataStore` existe déjà ;
- SQLite et PostgreSQL contiennent de la logique CRUD largement similaire ;
- Bandit a déjà détecté 4 `B608` sur la construction SQL PostgreSQL ;
- la Foundation n’a pas encore promis une compatibilité 1.0 ;
- SQLAlchemy prépare naturellement une trajectoire de migrations futures sans obliger à introduire Alembic maintenant.

## 11.3 SQLAlchemy Core avant ORM déclaratif

Le choix recommandé pour V0.1.6 est :

```text
SQLAlchemy Core
→ Table / Column
→ select / insert / update
→ Engine / Connection / Transaction
```

et non :

```text
faire de RunRecord / StepRecord des modèles ORM publics
```

Les objets PyIngestKit restent indépendants :

```text
DOMAIN / CONTRACT
RunRecord
StepRecord
ArtifactRecord
EventRecord
ValidationRecord
PublicationRecord

          │ mapping interne
          ▼

PERSISTENCE
SQLAlchemy tables / statements
```

## 11.4 Adapters conservés

Même avec une couche SQLAlchemy commune, conserver :

```text
SQLiteMetadataStore
PostgresMetadataStore
```

car les backends auront des besoins spécifiques.

SQLite peut notamment appliquer :

```text
PRAGMA foreign_keys = ON
journal_mode = WAL
busy_timeout
```

PostgreSQL pourra ultérieurement définir :

```text
pooling
SSL
statement timeout
schema dédié
```

## 11.5 Configuration cible

SQLite :

```yaml
metadata:
  backend: sqlite
  sqlite:
    path: null
```

`path: null` signifie :

```text
<runtime.workspace>/state/pyingest.sqlite3
```

PostgreSQL :

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL
```

Puis :

```bash
export PYINGEST_DATABASE_URL='postgresql://...'
```

Le framework peut normaliser en interne vers le dialecte SQLAlchemy/psycopg approprié afin de ne pas imposer au consommateur de connaître la syntaxe SQLAlchemy.

## 11.6 Garde-fous de persistence

- le `Runner` dépend uniquement de `MetadataStore` ;
- aucune classe SQLAlchemy dans l’API top-level ;
- aucun `Session`/`Base`/`Column` exposé aux jobs ;
- aucun SQL dynamique via f-string ;
- valeurs toujours bindées/paramétrées ;
- Peewee non introduit ;
- Alembic non introduit en V0.1.6 ;
- préparer une stratégie de version de schéma, mais ne pas lancer un chantier migrations complet avant besoin réel ;
- conserver des contract tests communs aux adapters.

## 11.7 Pourquoi ne pas intégrer Peewee

Peewee est un bon ORM léger, mais ajouter simultanément :

```text
SQLAlchemy + Peewee
```

créerait :

- deux abstractions concurrentes ;
- deux modèles de transactions ;
- deux conventions de query ;
- deux surfaces de maintenance ;
- aucun bénéfice fonctionnel pour l’utilisateur.

Décision :

```text
SQLAlchemy → OUI
Peewee     → NON
```

## 11.8 Migrations

SQLAlchemy prépare naturellement Alembic, mais **Alembic reste hors V0.1.6**.

Le besoin de migrations devra être déclenché par une vraie évolution de schéma à préserver en production, pas par anticipation.

# 12. Ajustement n°5 — Logs opérationnels vs Runtime Events

## 12.1 Ne pas confondre logs et métadonnées

Les logs complets servent au diagnostic humain et opérationnel.

Les événements servent à l’audit, l’historique et les requêtes structurées.

Architecture :

```text
                   Runtime
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
        Logs                    Events
          │                       │
          ▼                       ▼
Rich / JSON file           MetadataStore
```

## 12.2 Logs opérationnels

Conserver :

- DEBUG ;
- INFO ;
- WARNING ;
- ERROR ;
- CRITICAL ;
- tracebacks ;
- détails techniques.

Destinations :

```text
stderr
+
.pyingest/logs/pyingest.log
```

## 12.3 Events persistés

Événements recommandés :

```text
RUN_STARTED
STEP_STARTED
STEP_SUCCEEDED
STEP_FAILED
VALIDATION_COMPLETED
VALIDATION_FAILED
PUBLISH_STARTED
PUBLISH_SUCCEEDED
PUBLISH_FAILED
RUN_SUCCEEDED
RUN_FAILED
```

Garde-fou : **ne pas injecter chaque ligne DEBUG dans SQLite**.

Un event est un fait métier/runtime structuré ; un log est une trace opérationnelle.

---

# 13. Logging — Architecture officielle

Le choix à figer est :

```text
Python logging
        +
RichHandler
        +
structured JSON
        +
application-controlled handlers
```

Loguru n’est pas la convention interne du framework.

Les modules PyIngestKit et les plugins utilisent :

```python
import logging

logger = logging.getLogger(__name__)
```

Les modules ne configurent jamais les handlers à l’import.

La configuration se fait à la frontière applicative / CLI.

---

# 14. Format officiel du logging terminal

Le format terminal à figer est :

```text
2026-09-03 17:42:03  INFO   [run=785c1cdc job=demo.local_file] Run started
2026-09-03 17:42:03  INFO   [run=785c1cdc job=demo.local_file step=FetchLocal] Step started
2026-09-03 17:42:03  DEBUG  [run=785c1cdc job=demo.local_file step=FetchLocal] RAW artifact written
2026-09-03 17:42:03  INFO   [run=785c1cdc job=demo.local_file step=FetchLocal] Step succeeded 0.002s
2026-09-03 17:42:03  INFO   [run=785c1cdc job=demo.local_file] Run succeeded 0.003s
```

## 14.1 Règles

Terminal :

```text
Timestamp     YYYY-MM-DD HH:mm:ss
Timezone      locale
Run ID        8 premiers caractères
Job ID        complet
Step          affiché seulement si applicable
```

JSON / SQLite / PostgreSQL :

```text
Timestamp     ISO 8601 complet
Timezone      explicite
Run ID        UUID complet
```

## 14.2 Niveaux recommandés

INFO :

```text
Run started
Step started
Step succeeded
Step failed
Run succeeded
Run failed
```

DEBUG :

```text
plugin discovery
config merge
source path resolution
opening source
hash computation
RAW artifact written
manifest written
low-level adapter details
```

WARNING :

- anomalie non bloquante ;
- hook best-effort en échec ;
- configuration dépréciée ;
- fallback utilisé.

ERROR :

- step failed ;
- validation bloquante ;
- publication impossible ;
- run failed.

## 14.3 CLI verbosity

Ajouter :

```bash
pyingest run ... -v
```

→ `DEBUG`

```bash
pyingest run ... -q
```

→ `WARNING`

Conserver :

```bash
--log-level DEBUG
```

comme option explicite.

Garde-fou : les sorties `--json` restent sur stdout ; les logs restent sur stderr.

---

# 15. Configuration cible V0.1.x

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: false
  parameters: {}

metadata:
  backend: sqlite
  sqlite:
    path: .pyingest/state/pyingest.sqlite3

logging:
  level: INFO
  format: rich
  console: true

  file:
    enabled: true
    path: .pyingest/logs/pyingest.log
    level: DEBUG
    format: json
    max_bytes: 10000000
    backup_count: 5
```

Configuration PostgreSQL alternative :

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL
```

---

# 16. Redaction de secrets

La protection déjà introduite doit être conservée et testée.

Motifs typiques :

```text
password=...
token=...
api_key=...
client_secret=...
Authorization: Bearer ...
```

Sortie :

```text
token=***REDACTED***
```

Garde-fous :

- aucun secret dans les logs Rich ;
- aucun secret dans les fichiers JSON ;
- aucun secret dans MetadataStore ;
- paramètres sensibles à filtrer avant persistance ;
- DSN PostgreSQL lu via variable d’environnement.

---

# 17. Ajustement n°6 — Decorator API déclarative

## 17.1 Décision

PyIngestKit doit proposer les deux styles :

```text
Decorator API
→ recommandée / défaut

Imperative API
→ avancée / bas niveau / core
```

Architecture :

```text
            USER-FACING APIs

   Declarative              Imperative
    @job/@step             Job/Step/Pipeline
         │                       │
         └──────────┬────────────┘
                    ▼
            SAME INTERNAL MODEL
                    │
               Job / Pipeline
               Step definitions
               RunContext
                    │
                    ▼
                  Runner
```

Il ne doit y avoir qu’un seul moteur d’exécution.

---

# 18. Decorator API — Syntaxe cible

## 18.1 Cas simple

```python
from pyingestkit import job, step


@step
def fetch(context):
    ...


@step
def normalize(context):
    ...


@step
def validate(context):
    ...


@job(
    id="public.postal_codes",
    version="1.0.0",
    description="Official postal codes ingestion",
)
def postal_codes():
    fetch()
    normalize()
    validate()
```

Puis :

```bash
pyingest run public.postal_codes
```

## 18.2 Objectif de DX

Le code métier doit exprimer :

```text
voici mon job
voici ses étapes
voici leur ordre
```

et non exposer systématiquement les détails du moteur interne.

---

# 19. L’API impérative reste le contrat bas niveau

L’API impérative ne doit pas être supprimée.

Elle reste nécessaire pour :

- construction dynamique ;
- tests ;
- adapters ;
- extensions avancées ;
- pipelines générés programmatiquement ;
- composants internes ;
- cas nécessitant un contrôle explicite.

Exemple conceptuel :

```python
pipeline = Pipeline([
    FetchLocal(...),
    ValidateDataset(...),
    AtomicPublish(...),
])
```

Principe :

```text
Decorator API
= façade ergonomique

Imperative API
= modèle interne stable
```

---

# 20. Internals de la Declarative API

Structure recommandée :

```text
declarative/
├── decorators.py
├── job_definition.py
├── step_definition.py
├── invocation.py
└── builder.py
```

Objets à introduire :

```text
StepDefinition
StepInvocation
JobDefinition
PipelineBuilder
```

Distinction fondamentale :

```text
@step
function
   ↓
StepDefinition
```

puis :

```text
StepDefinition()
dans un @job
   ↓
StepInvocation
```

Un même step peut donc être invoqué plusieurs fois sans créer plusieurs définitions.

---

# 21. Build context — garde-fou important

Lors de :

```python
@job
def pipeline():
    fetch()
    normalize()
```

`fetch()` et `normalize()` ne doivent pas exécuter réellement les fonctions pendant la construction.

Le système doit fonctionner conceptuellement comme :

```text
@job function called
        │
        ▼
PipelineBuilder activated
        │
        ├── fetch()
        │      ↓
        │   register Fetch invocation
        │
        ├── normalize()
        │      ↓
        │   register Normalize invocation
        │
        ▼
Pipeline constructed
```

Puis seulement le `Runner` exécute le modèle construit.

---

# 22. Exécution directe pour les tests

Un décorateur ne doit pas rendre les fonctions métier difficiles à tester.

Convention recommandée :

```python
@step
def normalize(rows):
    ...
```

Dans un job :

```python
normalize()
```

→ enregistre une invocation.

Dans un test unitaire :

```python
normalize.fn(rows)
```

→ exécute la fonction Python réelle.

Garde-fou : ne pas créer une magie implicite où la même syntaxe exécute parfois et build parfois de manière incompréhensible.

---

# 23. Dataflow déclaratif — évolution contrôlée

Objectif futur possible :

```python
@job(...)
def postal_codes():
    raw = fetch()
    rows = parse(raw)
    normalized = normalize(rows)
    validated = validate(normalized)
    publish(validated)
```

Cette syntaxe est souhaitable car elle est :

- lisible ;
- typable ;
- testable ;
- déclarative ;
- proche du Python normal.

Mais garde-fou majeur : **ne pas transformer ce dataflow en moteur DAG généraliste**.

---

# 24. Ne pas recréer PyWorkflow Engine

La Decorator API peut reprendre un excellent pattern ergonomique de PyWorkflow Engine, mais pas son ambition générale d’orchestration.

À éviter dans PyIngestKit :

```text
parallel scheduler
worker pools
distributed DAG
branching engine
join engine
sensors
Celery workers
Kubernetes execution engine
generic workflow scheduler
```

Les dépendances éventuelles de steps doivent exprimer :

```text
ordre logique
dataflow
prérequis d’ingestion
```

pas :

```text
scheduling distribué
```

---

# 25. Timeout et retry — garde-fou

Éviter d’ajouter trop vite :

```python
@step(timeout=30)
```

sans contrat d’exécution solide.

Un timeout générique Python synchrone peut impliquer :

- threads ;
- processus ;
- signaux ;
- comportements non portables.

Pour V0.2, le timeout doit plutôt appartenir aux adapters qui peuvent réellement l’assurer, par exemple :

```text
HttpSource(timeout=30)
```

De même, le retry d’un fetch HTTP n’est pas nécessairement identique au retry d’un step arbitraire.

Garde-fou : ne pas transformer les décorateurs en “sac à options” avant de stabiliser leur sémantique.

---

# 26. Plugins et Decorator API

Le plugin loader doit accepter :

- `Job` ;
- `JobDefinition` ;
- éventuellement une factory explicite retournant l’un des deux.

Exemple :

```python
@job(
    id="demo.local_file",
    version="0.1.0",
    description="Local ingestion demonstration",
)
def local_file():
    fetch_local()
```

Entry point :

```toml
[project.entry-points."pyingestkit.jobs"]
demo-local-file = "pyingestkit_demo_jobs.local_file:local_file"
```

Le loader transforme :

```text
JobDefinition
   ↓
.build()
   ↓
Job / Pipeline
```

Le plugin demo doit être migré vers cette API pour devenir le Quickstart officiel.

---

# 27. CLI — Historique des runs

L’arrivée de MetadataStore rend possible une vraie CLI d’observabilité locale.

Ajouter :

```bash
pyingest runs
```

```bash
pyingest status <run_id>
```

Filtres possibles :

```bash
pyingest runs --job demo.local_file
pyingest runs --status FAILED
```

Exemple :

```text
Recent ingestion runs

Timestamp            Run       Job              Status    Duration
───────────────────  ────────  ───────────────  ────────  ────────
2026-09-03 17:42:24  e929e92c  demo.local_file  SUCCESS   0.002s
2026-09-03 17:42:18  b3bda149  demo.local_file  SUCCESS   0.002s
2026-09-03 17:41:54  ad664d5d  demo.local_file  FAILED    0.040s
```

---

# 28. CLI — `pyingest status`

Exemple cible :

```bash
pyingest status e929e92c
```

```text
Run e929e92c

Job        demo.local_file
Version    0.1.0
Status     SUCCESS
Started    2026-09-03 17:42:24
Duration   0.002s

Steps
────────────────────────────
FetchLocal    SUCCESS  0.002s

Artifacts
────────────────────────────
RAW sample.txt
SHA256 795458...
```

Garde-fou : le CLI doit lire le MetadataStore via son abstraction, sans dépendre directement de SQLite.

---

# 29. Manifest vs MetadataStore

Le manifest ne doit pas disparaître avec SQLite.

Les deux ont des rôles différents :

```text
manifest.json
→ snapshot portable et reproductible du run

MetadataStore
→ index interrogeable de l’historique des runs
```

Le manifest est utile pour :

- archivage ;
- transport ;
- replay ;
- audit fichier ;
- inspection hors base.

MetadataStore est utile pour :

- recherche ;
- liste ;
- filtres ;
- historiques ;
- dashboard ;
- statistiques ;
- état courant.

Garde-fou : ne pas remplacer l’un par l’autre.

---

# 30. Corriger les lacunes V0.1.x déjà identifiées

La consolidation doit aussi traiter plusieurs gaps connus.

## 30.1 Manifest et artefacts

Le Runner doit automatiquement enregistrer dans le manifest les artefacts significatifs produits par les steps.

Actuellement, un `RawArtifact` peut exister dans le `StepResult` sans forcément être répercuté automatiquement dans `manifest.artifacts`.

À corriger avant V0.2.

## 30.2 Validation et publication

La validation est disponible, mais le runtime doit préparer une intégration standard :

```text
validation report
     ↓
blocking decision
     ↓
publish allowed / denied
```

Sans pour autant imposer un workflow métier universel.

## 30.3 RAW immutability

`LocalArtifactStore.write_raw()` ne doit pas écraser silencieusement un fichier RAW portant le même nom dans un même run.

Stratégies possibles :

- fail-fast ;
- versionner/nommer explicitement ;
- suffixer par identifiant/hash.

La politique doit être explicite.

## 30.4 Hook lifecycle

Les hooks critiques doivent produire un `RunResult` et un état cohérent lorsque possible, plutôt que laisser certaines erreurs contourner le lifecycle et le manifest.

## 30.5 Registry

Éviter que le registry devienne un conteneur global de runtime actif.

Préférer :

```text
definitions / factories / specs
```

plutôt qu’état mutable global.

## 30.6 Plugin isolation

Un plugin cassé ne devrait pas empêcher toute la CLI de fonctionner si une erreur peut être isolée et reportée proprement.

Exemple futur :

```text
1 plugin loaded
1 plugin failed to load
```

avec diagnostic exploitable.

---

## 30.7 Manifest écrit en plusieurs phases

Les traces V0.1.5 montrent une écriture initiale puis une finalisation du manifest. Ce comportement n’est pas incorrect si les écritures sont atomiques, mais il doit être clarifié avant V1.0 :

- soit conserver explicitement un **checkpoint + finalization** ;
- soit construire le manifest en mémoire puis faire une seule écriture finale.

Ce point est du polishing et ne bloque pas V0.1.6 sauf si le refactoring persistence le rend trivial à simplifier.

## 30.8 `--json` et logs console

`pyingest run --json` produit son payload sur `stdout` et les logs sur `stderr`. Le terminal affiche les deux flux ensemble, mais une redirection :

```bash
pyingest run ... --json > result.json
```

reste machine-safe.

Garde-fou : ne pas mélanger réellement logs et payload JSON sur le même flux. Une éventuelle convention future `--json => console logging disabled` doit être décidée explicitement, pas introduite silencieusement.

## 30.9 Normalisation ISO 8601 des manifests

Les formats machine doivent converger vers :

```text
2026-09-03T17:03:31.824178+00:00
```

pour `started_at`, `completed_at`, `retrieved_at`, etc.

L’objectif est d’aligner manifest, JSON logs, SQLite/PostgreSQL et futures APIs.

# 31. Production-grade dependency policy

La Foundation consolidée doit conserver une politique explicite :

Runtime :

- Typer ;
- Rich ;
- Pydantic ;
- PyYAML ;
- driver PostgreSQL seulement si adapter PostgreSQL installé/activé selon stratégie retenue.

Dev toolchain :

- pytest ;
- pytest-cov ;
- pytest-randomly ;
- Ruff ;
- Mypy ;
- Bandit ;
- pip-audit ;
- pre-commit ;
- build ;
- twine.

Garde-fou : une dépendance ne doit pas devenir “core” uniquement parce qu’elle est populaire.

---

# 32. Structure source cible après consolidation

```text
src/pyingestkit/
│
├── core/
│   ├── job.py
│   ├── step.py
│   ├── pipeline.py
│   ├── context.py
│   ├── result.py
│   ├── registry.py
│   ├── events.py
│   ├── types.py
│   └── exceptions.py
│
├── declarative/
│   ├── decorators.py
│   ├── job_definition.py
│   ├── step_definition.py
│   ├── invocation.py
│   └── builder.py
│
├── runtime/
│   ├── runner.py
│   ├── lifecycle.py
│   └── replay.py
│
├── metadata/
│   ├── base.py
│   ├── sqlite.py
│   └── postgres.py
│
├── logging/
│   ├── setup.py
│   ├── formatters.py
│   ├── filters.py
│   └── context.py
│
├── config/
│   ├── models.py
│   └── loader.py
│
├── sources/
│   ├── base.py
│   └── local.py
│
├── artifacts/
│   ├── base.py
│   ├── raw.py
│   ├── filesystem.py
│   └── layout.py
│
├── provenance/
│   ├── hashing.py
│   ├── manifest.py
│   └── metadata.py
│
├── validation/
│   ├── contracts.py
│   ├── rules.py
│   ├── references.py
│   ├── severity.py
│   └── report.py
│
├── publication/
│   ├── atomic.py
│   ├── staging.py
│   ├── published.py
│   └── diff.py
│
├── targets/
│   └── base.py
│
├── plugins/
│   ├── registry.py
│   ├── discovery.py
│   └── entrypoints.py
│
└── cli/
    ├── app.py
    ├── common.py
    ├── console.py
    └── commands/
        ├── jobs.py
        ├── inspect.py
        ├── run.py
        ├── runs.py
        └── status.py
```

---

# 33. Tests à ajouter avant V0.2

## 33.1 MetadataStore

```text
tests/unit/metadata/
├── test_metadata_contract.py
├── test_sqlite_store.py
└── test_postgres_contract.py
```

Le test de contrat doit être réutilisable par plusieurs backends.

## 33.2 Declarative API

```text
tests/unit/declarative/
├── test_step_decorator.py
├── test_job_decorator.py
├── test_pipeline_builder.py
├── test_step_invocation.py
└── test_direct_function_execution.py
```

## 33.3 Runtime

```text
tests/integration/
├── test_run_metadata.py
├── test_run_events.py
├── test_declarative_job.py
├── test_manifest_artifacts.py
└── test_failed_run_persistence.py
```

## 33.4 CLI

Ajouter :

```text
test_runs_command
test_status_command
test_verbose
test_quiet
test_json_stdout_not_polluted
test_plugin_failure_isolated
```

## 33.5 Workspace

Tester :

- workspace par défaut unique ;
- override CLI ;
- pas de `.pyingest-demo` créé implicitement ;
- layout déterministe.

---

# 34. Tests d’acceptation end-to-end

Avant V0.2, un environnement vierge doit permettre :

```bash
python -m pip install -e ".[dev]"
python -m pip install -e examples/plugin_package
```

Puis :

```bash
pyingest --version
pyingest jobs
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs
pyingest status <run_id>
```

Le résultat attendu :

- plugin découvert ;
- job construit via Decorator API ;
- runtime impératif utilisé sous le capot ;
- logs terminal Rich visibles ;
- fichier JSON de logs écrit ;
- run persistant en SQLite ;
- steps persistés ;
- artefacts persistés en metadata ;
- manifest écrit ;
- CLI `runs` affiche le run ;
- CLI `status` affiche le détail ;
- aucun second workspace créé.

---

# 35. CI / Quality Gates — état réel et cible V0.1.6

## 35.1 État observé sur V0.1.5

Les tests fonctionnels sont verts :

```text
pytest                 55 passed
unittest               54 passed
public API contract    OK
compileall             OK
build                   OK avec warnings packaging
```

En revanche :

```text
make quality
→ FAIL
→ Ruff : 56 erreurs

make security
→ FAIL
→ Bandit : 4 B608 Medium / Medium
```

Conséquences :

- `mypy --strict` n’est pas encore prouvé green si Ruff arrête la target avant ;
- `pip-audit` n’est pas encore prouvé green si Bandit arrête la target avant ;
- le build réussit mais Setuptools remonte une dépréciation sur `project.license` au format table et sur le classifier MIT.

## 35.2 Ruff

Les findings actuels incluent notamment :

```text
I001   imports non triés
UP017  datetime.UTC
UP035  collections.abc
UP037  annotations modernes
F401   imports inutilisés
B009   getattr constant
BLE001 broad exception catches
```

La majorité est auto-fixable, mais la règle est :

```text
ruff check --fix
→ OUI après review

--unsafe-fixes
→ NON par défaut
```

Les `except Exception` doivent être évalués par frontière :

- **plugin discovery boundary** : catch large légitime pour isoler un plugin tiers ;
- **user-code execution boundary dans Runner** : catch large légitime pour convertir une exception arbitraire en `FAILED RunResult` ;
- **logging handler** : catch large potentiellement légitime pour respecter le contrat `logging.Handler.handleError`.

Lorsque le catch large est volontaire, le code doit contenir une justification locale explicite plutôt qu’une suppression globale de `BLE001`.

## 35.3 Bandit

Les 4 `B608` proviennent de constructions de requêtes PostgreSQL contenant une interpolation de colonnes SQL.

Même si les valeurs utilisateur sont paramétrées, la cible V0.1.6 est :

```text
aucune f-string SQL
aucune concaténation SQL dynamique
SQLAlchemy expressions / bound parameters
```

Ne pas résoudre ce sujet par `# nosec` lorsque le refactoring SQLAlchemy permet de supprimer la cause.

## 35.4 Mypy strict

Après Ruff :

```bash
mypy src/pyingestkit
```

doit terminer avec exit code `0` sous la configuration stricte du projet.

Aucun “type: ignore” global ou massif ne doit être ajouté pour faire passer artificiellement le gate.

## 35.5 pip-audit

Après Bandit :

```bash
pip-audit
```

doit être exécuté réellement et documenté.

Une vulnérabilité ne doit pas être masquée sans justification et plan de remédiation.

## 35.6 Packaging PEP 639

Remplacer :

```toml
license = { text = "MIT" }
```

par :

```toml
license = "MIT"
```

et retirer le classifier de licence devenu redondant si nécessaire.

Objectif : build sans warnings de dépréciation Setuptools liés à la licence.

## 35.7 Targets Make recommandées

```makefile
format:
	ruff check --fix src tests examples/plugin_package/src examples/plugin_package/tests
	ruff format src tests examples/plugin_package/src examples/plugin_package/tests

quality:
	ruff check src tests examples/plugin_package/src examples/plugin_package/tests
	ruff format --check src tests examples/plugin_package/src examples/plugin_package/tests
	mypy src/pyingestkit

security:
	bandit -r src/pyingestkit
	pip-audit

verify:
	$(MAKE) check
	$(MAKE) quality
	$(MAKE) security
	$(MAKE) build
```

Le gate ultime devient :

```bash
make verify
```

avec :

```text
exit code = 0
```

## 35.8 Définition stricte de “green”

La Foundation n’est pas “green” parce que les tests passent. Elle est green lorsque :

```text
tests
+ static analysis
+ strict typing
+ security scan
+ dependency audit
+ packaging
+ wheel install smoke
```

sont tous verts.

# 36. ADR à créer / mettre à jour

## ADR Foundation déjà introduits avec V0.1.5

```text
ADR-012 — Unified workspace layout
ADR-013 — MetadataStore abstraction
ADR-014 — SQLite as default metadata backend
ADR-015 — Operational logs vs runtime events
ADR-016 — Declarative decorator API
ADR-017 — Decorator API compiles to imperative model
```

Ils doivent être relus afin de vérifier qu’ils décrivent l’état réellement livré en V0.1.5 et non uniquement l’intention initiale.

## ADR à ajouter pour V0.1.6

```text
ADR-018 — SQLAlchemy 2.x as metadata persistence engine
ADR-019 — One persistence engine: SQLAlchemy; Peewee rejected
ADR-020 — Foundation quality/security gate and make verify policy
ADR-021 — Schema evolution strategy: no Alembic before demonstrated need
```

ADR-018 doit expliciter :

- SQLAlchemy Core privilégié ;
- `MetadataStore` demeure le contrat ;
- pas de fuite ORM dans les records/core ;
- SQLite et PostgreSQL utilisent un repository commun lorsque pertinent ;
- spécificités backend conservées dans les adapters.

ADR-020 doit figer :

```text
make verify = 0
```

comme condition d’ouverture de V0.2.

## ADR à mettre à jour

```text
ADR-010 — Production-grade dependency policy
ADR-011 — Logging policy
ADR-013 — MetadataStore abstraction
ADR-014 — SQLite as default metadata backend
```

ADR-010 doit intégrer SQLAlchemy et la décision de ne pas ajouter Peewee.

ADR-011 doit conserver :

- timestamp terminal ;
- contexte court ;
- niveaux INFO/DEBUG ;
- stdout/stderr ;
- JSON structuré ;
- redaction de secrets.

## ADR historiques

Les ADR remplacés doivent rester présents et marqués `SUPERSEDED`, plutôt que supprimés.

# 37. Documentation à créer / enrichir

La V0.1.5 possède déjà une base documentaire importante. Avant le freeze V0.1.6, compléter ou vérifier :

```text
docs/architecture/
├── workspace.md
├── metadata-store.md
├── logging.md
├── declarative-api.md
├── runtime-events.md
├── plugin-model.md
└── persistence-sqlalchemy.md        # V0.1.6
```

Guides :

```text
docs/guides/
├── write-a-job-with-decorators.md
├── write-a-job-imperative.md
├── configure-metadata-store.md
├── configure-postgres-metadata.md   # V0.1.6
├── inspect-run-history.md
└── package-a-job-plugin.md
```

Tutoriel démo :

```text
docs/tutorials/demo-plugin.md
```

La documentation V0.1.6 doit également expliquer :

- pourquoi SQLAlchemy est interne ;
- pourquoi Peewee n’est pas intégré ;
- comment SQLite reste le défaut zéro-infrastructure ;
- comment PostgreSQL devient un adapter partagé ;
- ce que vérifie `make verify` ;
- quelles exceptions Ruff/Bandit sont volontairement justifiées et lesquelles doivent être supprimées.

# 38. README — nouvelle hiérarchie

Le Quickstart doit présenter d’abord :

```text
Decorator API
```

Exemple :

```python
from pyingestkit import job, step
```

Puis une section :

```text
Advanced — Imperative API
```

L’utilisateur standard ne doit pas avoir besoin de connaître toutes les classes internes pour créer son premier job.

---

# 39. API publique cible

À terme, le top-level package devrait permettre :

```python
from pyingestkit import (
    job,
    step,
    Job,
    Step,
    Pipeline,
    RunContext,
    Runner,
)
```

Avec :

```text
@job / @step
→ Recommended

Job / Step / Pipeline
→ Advanced / Core
```

Garde-fou : maintenir une surface publique réduite et documentée ; les classes internes de builder ne doivent pas nécessairement être exposées au top-level.

---

# 40. Garde-fous de design pour la Foundation

## 40.1 Pas de God Framework

Toute nouvelle abstraction doit avoir une responsabilité claire.

## 40.2 Pas de scheduler

`Runner` exécute un job ; il ne planifie pas quand le job doit démarrer.

## 40.3 Pas de DAG distribué

Le dataflow déclaratif n’autorise pas automatiquement la création d’un orchestrateur parallèle.

## 40.4 Pas de secret dans la config versionnée

Secrets via environnement / secret manager externe.

## 40.5 Pas de dépendance directe du core à SQLite/Postgres

Dépendre de `MetadataStore`.

## 40.6 Pas de couplage plugin → workspace global

Le workspace appartient au runtime/configuration.

## 40.7 Pas de logs = events

Les logs restent opérationnels ; les events restent structurés.

## 40.8 Pas de publication sans validation explicite lorsque requise

Les jobs restent responsables de leur politique métier, mais le framework doit permettre des gates standards.

## 40.9 Pas de mutation silencieuse des RAW

RAW doit rester immuable dans le lifecycle.

## 40.10 Pas de magie excessive dans les decorators

Le build doit être déterministe, introspectable et testable.

---

# 41. Définition de Done — Foundation V0.1.x

## 41.1 Acquis fonctionnels V0.1.5

### Architecture

- [x] un seul workspace par défaut `.pyingest/` ;
- [x] `ArtifactStore` et `MetadataStore` distincts ;
- [x] `Runner` dépend de `MetadataStore`, pas de SQLite ;
- [x] SQLite backend metadata par défaut ;
- [x] PostgreSQL adapter contract présent ;
- [x] manifest et metadata complémentaires.

### Runtime

- [x] runs persistés ;
- [x] steps persistés ;
- [x] failures persistées ;
- [x] artefacts principaux référencés ;
- [x] événements structurants persistés ;
- [x] RAW immuable ;
- [x] lifecycle critique couvert par tests.

### Logging

- [x] format terminal officiel appliqué ;
- [x] timestamp local `YYYY-MM-DD HH:mm:ss` ;
- [x] run ID court ;
- [x] UUID complet en JSON/DB ;
- [x] lifecycle step en INFO ;
- [x] détails internes en DEBUG ;
- [x] `-v` ;
- [x] `-q` ;
- [x] séparation stdout/stderr ;
- [x] secrets redacted.

### Declarative API

- [x] `@step` ;
- [x] `@job` ;
- [x] `StepDefinition` ;
- [x] `StepInvocation` ;
- [x] `JobDefinition` ;
- [x] `PipelineBuilder` ;
- [x] compilation vers le modèle impératif ;
- [x] `.fn()` pour tests directs ;
- [x] plugin loader compatible ;
- [x] demo migrée vers decorators.

### CLI

- [x] `jobs` ;
- [x] `inspect` ;
- [x] `run` ;
- [x] `runs` ;
- [x] `status` ;
- [x] `--json` machine-safe au niveau des flux ;
- [x] verbosity flags.

## 41.2 Blocants V0.1.6 avant V0.2

### Persistence hardening

- [x] SQLAlchemy 2.x intégré ;
- [x] SQLAlchemy Core utilisé pour le repository metadata ;
- [x] SQLite adapter migré ;
- [x] PostgreSQL adapter migré ;
- [x] aucun SQL dynamique via f-string ;
- [x] Peewee non introduit ;
- [x] SQLAlchemy absent de l’API publique métier ;
- [x] SQLite tuning minimum documenté/testé ;
- [x] tests de contrat backend toujours verts.

### Quality / Security

- [ ] Ruff = 0 erreur ;
- [ ] Ruff format --check vert ;
- [ ] Mypy strict vert ;
- [ ] Bandit = 0 finding bloquant ;
- [ ] pip-audit exécuté et vert ou exceptions explicitement documentées ;
- [x] packaging PEP 639 propre ;
- [x] build sans warnings de licence Setuptools ;
- [x] wheel install smoke vert ;
- [x] plugin wheel smoke vert ;
- [ ] `make verify` exit code `0` ;
- [ ] CI reproduit exactement les mêmes gates.

### Documentation

- [x] ADR persistence SQLAlchemy ajouté ;
- [x] ADR dependency policy mis à jour ;
- [x] document Foundation reflète l’état réel ;
- [x] changelog V0.1.6 complet.

## 41.3 Condition d’ouverture de V0.2

> **V0.2 ne démarre que lorsque tous les items V0.1.6 ci-dessus sont satisfaits ou explicitement dérogés par une décision d’architecture documentée.**

# 42. Ce qui reste explicitement hors V0.1.x

Ne pas profiter du chantier Foundation pour ajouter :

- HTTP source complet ;
- retry/backoff réseau ;
- CSV parser ;
- JSON parser ;
- Excel parser ;
- HTML parser ;
- Dataset Contracts avancés ;
- diff engine complet ;
- replay complet ;
- PostgresTarget métier ;
- Alembic/migrations complètes tant qu’aucune compatibilité de schéma réelle n’est à préserver ;
- Peewee ou second ORM ;
- S3 ;
- MinIO ;
- scheduler ;
- parallel DAG ;
- Celery ;
- Kubernetes ;
- UI web ;
- Data Catalog ;
- RBAC ;
- AI/Agents/RAG.

Ces sujets appartiennent aux versions suivantes ou à des composants externes.

---

# 43. Périmètre prévu de V0.2 après stabilisation

Une fois les critères précédents satisfaits, V0.2 peut commencer avec :

```text
Acquisition
────────────────────────────
HTTP source / client
RetryPolicy
Timeout réseau
CSV
JSON
Dataset Contracts
```

V0.2 pourra alors s’appuyer sur :

- un runtime stable ;
- une API utilisateur stable ;
- un workspace stable ;
- une persistance stable ;
- une observabilité stable ;
- un plugin model stable ;
- des conventions de configuration stables.

---

# 44. Roadmap recommandée

## V0.1.5 — Foundation Consolidation — IMPLEMENTED

Scope livré :

```text
Unified workspace
MetadataStore contract
SQLite backend
Postgres adapter contract
Run / step / artifact / event persistence
Logging terminal final
-v / -q
runs/status CLI
Decorator API
Demo migration
Manifest integration fixes
RAW immutability
Plugin isolation
ADR / docs / CI definitions
```

Statut : **V0.1.5 fonctionnellement vert ; V0.1.6 implémente le hardening persistence, les quality/security gates restent le critère de freeze à exécuter dans l’environnement dev/CI de référence**.

## V0.1.6 — Foundation Persistence & Quality Hardening — IMPLEMENTED / GATES TO VERIFY

Scope strict :

```text
SQLAlchemy 2.x dependency
SQLAlchemy Core persistence layer
Common metadata repository
SQLite adapter refactor
PostgreSQL adapter refactor
psycopg optional extra
SQLite foreign_keys / WAL / busy_timeout policy
Remove dynamic raw SQL
Ruff 0
Ruff format green
Mypy strict green
Bandit green
pip-audit green
PEP 639 packaging clean
make verify = 0
wheel smoke tests
CI parity
```

Explicitement hors scope V0.1.6 :

```text
HTTP
Retry réseau
CSV / JSON parsers
Dataset Contracts
Alembic complet
Peewee
nouveau scheduler
nouveau DAG engine
```

## V0.2 — Acquisition

```text
HTTP
Retry
CSV
JSON
Dataset Contracts
```

## V0.3 — Quality / formats

```text
Excel
HTML
Validation reports
Reference checks
```

## V0.4 — Reproducibility / versioning

```text
Diff engine
PublishedDataset
Replay
```

## V0.5 — Persistence targets

```text
PostgresTarget
PostgreSQL metadata hardened
Bulk load
```

## V0.6 — Object storage conditionnel

Seulement si les pilotes démontrent le besoin :

```text
S3ArtifactStore
MinioArtifactStore
```

## V1.0 — Stable

Critères :

- API publique stable ;
- scope stable ;
- CI verte ;
- docs complètes ;
- plugins stables ;
- au moins deux vrais packs métiers ;
- replay validé ;
- publication atomique validée ;
- politique de sécurité documentée.

# 45. Pilotes de référence après Foundation

Les pilotes restent :

```text
Pilote 1
countries → localities → postal_codes
```

```text
Pilote 2
sectors → employers → jobs/professions
```

Ils permettront de vérifier que la Foundation reste générique et n’est pas contaminée par un domaine particulier.

---

# 46. Décisions à figer

Les décisions consolidées sont :

1. **Decorator API par défaut** pour les auteurs de jobs.
2. **Imperative API conservée** comme modèle bas niveau stable.
3. **Un seul runtime** pour les deux APIs.
4. **Un seul workspace par défaut** `.pyingest/`.
5. **ArtifactStore distinct du MetadataStore**.
6. **SQLite MetadataStore par défaut**.
7. **PostgreSQL backend interchangeable** pour les environnements partagés.
8. **SQLAlchemy 2.x devient le moteur interne de persistence metadata en V0.1.6**.
9. **SQLAlchemy Core privilégié** pour la Foundation ; pas d’ORM déclaratif qui contamine les records métier.
10. **Peewee non intégré** : un seul moteur de persistence suffit.
11. **psycopg reste optionnel** via extra PostgreSQL.
12. **Alembic différé** jusqu’à l’apparition d’un vrai besoin de migrations de schéma compatibles.
13. **Logs opérationnels distincts des events runtime**.
14. **Python logging + Rich** comme convention.
15. **Format terminal timestampé** figé.
16. **JSON logs structurés** pour fichiers/collecte.
17. **Secrets redacted**.
18. **CLI runs/status** fait partie de la Foundation.
19. **Pas de scheduler/DAG engine**.
20. **Pas de timeout/retry générique non maîtrisé dans `@step`**.
21. **Manifest conservé même avec SQLite/PostgreSQL**.
22. **RAW immuable**.
23. **Tests de contrats obligatoires pour adapters/plugins**.
24. **Aucune SQL f-string dynamique dans les adapters**.
25. **Les broad exception catches légitimes sont documentés localement aux frontières plugin/user-code**.
26. **`make verify` exit 0 devient la définition opérationnelle du freeze Foundation**.
27. **V0.2 ne commence pas avant le hardening V0.1.6**.

# 47. Architecture cible finale avant V0.2

```text
                              PyIngestKit
                                   │
                 ┌─────────────────┴──────────────────┐
                 │                                    │
                 ▼                                    ▼
         Decorator API                         Imperative API
         @job / @step                        Job / Step / Pipeline
                 │                                    │
                 └─────────────────┬──────────────────┘
                                   │
                                   ▼
                              SAME MODEL
                                   │
                                   ▼
                                Runner
                                   │
            ┌──────────────────────┼────────────────────────┐
            │                      │                        │
            ▼                      ▼                        ▼
       ArtifactStore          MetadataStore              Logging
            │                      │                        │
            ▼                      ▼                 ┌──────┴──────┐
      Local filesystem       SQLAlchemy 2.x          ▼             ▼
                            Core repository       Rich        JSON file
                                  │               stderr
                         ┌────────┴────────┐
                         ▼                 ▼
                      SQLite          PostgreSQL
                    default local      shared/server
                         │                 │
                    stdlib driver      psycopg extra
```

Workspace :

```text
.pyingest/
├── logs/
│   └── pyingest.log
├── runs/
│   └── <namespace>/<job>/<run_id>/...
├── state/
│   └── pyingest.sqlite3
└── published/
    └── ...
```

Responsabilités :

```text
ArtifactStore
→ RAW / staging / candidate / reports / manifests / published datasets

MetadataStore
→ runs / steps / artifact metadata / validations / publications / events

SQLAlchemy
→ persistence implementation detail only

Logging
→ diagnostic humain/opérationnel

Events
→ faits structurés persistables
```

# 48. Conclusion

La V0.1.x constitue le **contrat de fondation** sur lequel reposeront tous les futurs jobs et packages PyIngestKit.

La V0.1.5 a démontré que les décisions fonctionnelles principales sont cohérentes :

```text
workspace
runtime
plugins
declarative API
metadata
SQLite
logging
manifest
run history
```

Mais les quality/security gates réels ont apporté une information essentielle :

> **une Foundation production-grade n’est pas stabilisée tant que les tests fonctionnels sont verts mais que les gates statiques/sécurité échouent.**

Le bon ordre devient donc :

```text
V0.1.5
VALIDER LE COMPORTEMENT
          ↓
V0.1.6
HARDEN LA PERSISTENCE
          ↓
UNIFIER SQLITE / POSTGRES VIA SQLALCHEMY
          ↓
RENDRE RUFF / MYPY / BANDIT / PIP-AUDIT VERTS
          ↓
NETTOYER LE PACKAGING
          ↓
make verify = 0
          ↓
FIGER LA FOUNDATION
          ↓
ENSUITE OUVRIR V0.2
```

La cible finale avant V0.2 est donc une **V0.1.6 “Foundation Persistence & Quality Hardening”**, avec un scope volontairement fermé.

Le garde-fou ultime reste :

> **PyIngestKit doit être excellent pour l’ingestion, pas moyen dans tous les domaines de la Data Platform.**
