# PyIngestKit — Stabilisation de la Foundation V0.1.x avant V0.2

**Document de référence d’architecture et de stabilisation**  
**Projet :** PyIngestKit  
**Périmètre :** Foundation V0.1.x  
**Cible de consolidation :** V0.1.5 — Foundation Consolidation  
**Étape suivante autorisée :** V0.2 — Acquisition & Dataset Contracts  
**Date :** 2026-09-03  
**Statut :** Proposition consolidée à figer avant V0.2

> **Implementation note — V0.1.5:** this repository implements the Foundation Consolidation described by this plan. The document is retained as the design baseline and guardrail reference.

---

## 0. Résumé exécutif

PyIngestKit a atteint en V0.1.4 un premier socle exécutable et démontrable : CLI Typer/Rich, plugins Python via entry points, exécution de jobs, artefacts RAW, SHA-256, manifest, validation basique, publication atomique, configuration YAML/Pydantic, logging structuré et package de démonstration installable.

Avant d’ajouter les capacités V0.2 (`HTTP`, retry, CSV/JSON, Dataset Contracts), plusieurs fondations doivent toutefois être **stabilisées** afin d’éviter de propager des choix transitoires dans tous les futurs jobs et plugins.

La consolidation V0.1.x doit notamment figer :

1. un **workspace unique** `.pyingest/` ;
2. une séparation claire entre **ArtifactStore** et **MetadataStore** ;
3. **SQLite comme MetadataStore par défaut**, avec PostgreSQL comme adapter ;
4. la distinction entre **logs opérationnels** et **événements runtime persistés** ;
5. un format terminal Rich stable avec timestamp, niveau, contexte de run/job/step ;
6. une **Decorator API `@job` / `@step`** recommandée par défaut ;
7. le maintien de l’API impérative comme contrat bas niveau et API avancée ;
8. une doctrine stricte empêchant PyIngestKit de dériver vers un orchestrateur DAG, un scheduler distribué ou une plateforme généraliste ;
9. un jeu de tests de contrat garantissant que les backends, plugins et APIs restent interchangeables ;
10. des critères de sortie explicites avant toute ouverture du chantier V0.2.

La cible est donc :

```text
V0.1.4
────────────────────────────────
CLI
Plugins
RAW
Manifest
Validation basique
Publication atomique
Configuration YAML/Pydantic
Logging Rich + JSON

                ↓

V0.1.5
FOUNDATION CONSOLIDATION
────────────────────────────────
Workspace unifié
MetadataStore
SQLite par défaut
PostgreSQL adapter contract
Runtime events persistés
Logging terminal stabilisé
-v / -q
CLI runs / status
Decorator API @job / @step
Builder déclaratif → modèle impératif
Plugin demo migré vers decorators
Tests de contrats / intégration renforcés
ADR consolidés

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

---

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

# 5. État actuel atteint en V0.1.4

## 5.1 Core / Runtime

La V0.1.4 possède déjà :

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
- gestion des erreurs structurées ;
- hooks best-effort / critical.

## 5.2 Artefacts / provenance

Déjà disponibles :

- `LocalArtifactStore` ;
- layout de run ;
- `RawArtifact` ;
- SHA-256 ;
- `RunManifest` ;
- écriture JSON atomique ;
- publication atomique via remplacement de fichier.

## 5.3 Sources

Déjà disponible :

- `LocalSource`.

## 5.4 Validation

Déjà disponibles :

- `ValidationSeverity` ;
- `ValidationIssue` ;
- `ValidationReport` ;
- `ValidationRule` ;
- `MinimumRows` ;
- `RequiredField` ;
- `UniqueField`.

## 5.5 Configuration

Déjà disponibles :

- `PyYAML` ;
- `Pydantic` ;
- validation stricte `extra="forbid"` ;
- `pyingest.yml` ;
- paramètres runtime ;
- précédence de configuration.

Ordre de précédence actuel/cible :

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

## 5.6 CLI

La CLI repose désormais sur :

- Typer ;
- Rich.

Commandes :

```text
pyingest jobs
pyingest inspect
pyingest run
pyingest help
```

Sorties machine :

```text
--json
--version
```

ne doivent pas être polluées par les codes ANSI Rich.

## 5.7 Plugins

Découverte via :

```toml
[project.entry-points."pyingestkit.jobs"]
```

Le package démo est installable séparément et démontre correctement :

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

## 5.8 Logging

La V0.1.4 utilise :

```text
Python logging
      +
RichHandler
      +
JSON file logging
      +
RotatingFileHandler
```

Le framework utilise :

```python
logging.getLogger(__name__)
```

et ne configure pas les handlers à l’import.

---

# 6. Politique de dépendances

La contrainte historique `zero third-party dependency` est abandonnée.

La doctrine devient :

> PyIngestKit peut utiliser des dépendances tierces reconnues lorsque cela améliore la robustesse, la maintenabilité, la sécurité, la DX ou l’industrialisation.

Dépendances de socle déjà retenues :

- `Typer` ;
- `Rich` ;
- `Pydantic` ;
- `PyYAML`.

Le principe n’est donc pas :

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
- `pip-audit` dans le toolchain dev/CI ;
- changelog des changements de dépendances majeurs ;
- extras uniquement lorsque la dépendance est réellement optionnelle.

---

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

# 11. Ajustement n°4 — PostgreSQL comme adapter

## 11.1 Objectif

PostgreSQL doit devenir utile lorsqu’on passe à :

- plusieurs machines ;
- plusieurs workers ;
- historique partagé ;
- observabilité centralisée ;
- dashboard partagé ;
- forte concurrence ;
- besoin de durabilité serveur.

## 11.2 Configuration cible

SQLite :

```yaml
metadata:
  backend: sqlite
  sqlite:
    path: .pyingest/state/pyingest.sqlite3
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

Garde-fou sécurité : **ne pas placer le DSN ou mot de passe PostgreSQL directement dans le YAML versionné**.

## 11.3 Portabilité

SQLite et PostgreSQL doivent passer une suite commune :

```text
MetadataStore contract tests
```

Le runtime ne doit pas contenir :

```python
if backend == "sqlite":
    ...
elif backend == "postgres":
    ...
```

partout dans le code.

La sélection du backend doit se faire à la composition/configuration, pas au cœur du lifecycle.

---

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

# 35. CI / Quality Gates

La Foundation consolidée doit avoir des gates automatiques au minimum sur :

```text
compileall
pytest
coverage
ruff
mypy
bandit
pip-audit
build wheel
wheel install smoke test
plugin install smoke test
CLI smoke tests
```

Recommandation : ajouter les workflows CI avant V0.2 si toujours absents.

Garde-fou : une feature Foundation n’est pas “Done” uniquement parce qu’elle fonctionne dans un checkout editable local.

Elle doit aussi fonctionner depuis les wheels construits.

---

# 36. ADR à créer / mettre à jour

## ADR nouveaux

```text
ADR-012 — Unified workspace layout
ADR-013 — MetadataStore abstraction
ADR-014 — SQLite as default metadata backend
ADR-015 — Operational logs vs runtime events
ADR-016 — Declarative decorator API
ADR-017 — Decorator API compiles to imperative model
```

## ADR à mettre à jour

```text
ADR-011 — Logging policy
```

pour intégrer :

- timestamp terminal ;
- contexte court ;
- niveaux INFO/DEBUG ;
- stdout/stderr ;
- JSON structuré ;
- redaction de secrets.

## ADR historiques

Les ADR remplacés doivent rester présents et marqués `SUPERSEDED`, plutôt que supprimés.

---

# 37. Documentation à créer / enrichir

```text
docs/architecture/
├── workspace.md
├── metadata-store.md
├── logging.md
├── declarative-api.md
├── runtime-events.md
└── plugin-model.md
```

Guides :

```text
docs/guides/
├── write-a-job-with-decorators.md
├── write-a-job-imperative.md
├── configure-metadata-store.md
├── inspect-run-history.md
└── package-a-job-plugin.md
```

Tutoriel démo :

```text
docs/tutorials/demo-plugin.md
```

à migrer vers `@job` / `@step`.

---

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

La Foundation est considérée stabilisée seulement si :

### Architecture

- [ ] un seul workspace par défaut `.pyingest/` ;
- [ ] `ArtifactStore` et `MetadataStore` sont distincts ;
- [ ] `Runner` dépend de `MetadataStore`, pas de SQLite ;
- [ ] SQLite est le backend metadata par défaut ;
- [ ] PostgreSQL satisfait le même contrat ou possède au minimum un adapter contract figé ;
- [ ] manifest et metadata restent complémentaires.

### Runtime

- [ ] runs persistés ;
- [ ] steps persistés ;
- [ ] failures persistées ;
- [ ] artefacts principaux référencés ;
- [ ] événements structurants persistés ;
- [ ] lifecycle cohérent même en cas d’erreur critique.

### Logging

- [ ] format terminal officiel appliqué ;
- [ ] timestamp local `YYYY-MM-DD HH:mm:ss` ;
- [ ] run ID court ;
- [ ] UUID complet en JSON/DB ;
- [ ] lifecycle step en INFO ;
- [ ] détails internes en DEBUG ;
- [ ] `-v` ;
- [ ] `-q` ;
- [ ] JSON stdout non pollué ;
- [ ] secrets redacted.

### Declarative API

- [ ] `@step` ;
- [ ] `@job` ;
- [ ] `StepDefinition` ;
- [ ] `StepInvocation` ;
- [ ] `JobDefinition` ;
- [ ] `PipelineBuilder` ;
- [ ] compilation vers le modèle impératif ;
- [ ] `.fn()` pour tests directs ;
- [ ] plugin loader compatible ;
- [ ] demo migrée vers decorators.

### CLI

- [ ] `jobs` ;
- [ ] `inspect` ;
- [ ] `run` ;
- [ ] `runs` ;
- [ ] `status` ;
- [ ] `--json` machine-safe ;
- [ ] verbosity flags.

### Quality

- [ ] unit tests verts ;
- [ ] integration tests verts ;
- [ ] contract tests verts ;
- [ ] wheel build vert ;
- [ ] wheel install smoke vert ;
- [ ] plugin wheel smoke vert ;
- [ ] Ruff vert ;
- [ ] Mypy vert ;
- [ ] Bandit vert ;
- [ ] pip-audit contrôlé ;
- [ ] docs/ADR à jour.

---

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

## V0.1.5 — Foundation Consolidation

Scope :

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
RAW immutability fix
Plugin isolation improvements
ADR / docs / CI gates
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

---

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

Les décisions proposées sont donc :

1. **Decorator API par défaut** pour les auteurs de jobs.
2. **Imperative API conservée** comme modèle bas niveau stable.
3. **Un seul runtime** pour les deux APIs.
4. **Un seul workspace par défaut** `.pyingest/`.
5. **SQLite MetadataStore par défaut**.
6. **PostgreSQL comme adapter interchangeable**.
7. **ArtifactStore distinct du MetadataStore**.
8. **Logs opérationnels distincts des events runtime**.
9. **Python logging + Rich** comme convention.
10. **Format terminal timestampé** figé.
11. **JSON logs structurés** pour fichiers/collecte.
12. **Secrets redacted**.
13. **CLI runs/status** avant V0.2.
14. **Pas de scheduler/DAG engine**.
15. **Pas de timeout/retry générique non maîtrisé dans `@step`**.
16. **Manifest conservé même avec SQLite**.
17. **RAW immuable**.
18. **Tests de contrats obligatoires pour adapters/plugins**.

---

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
            ▼              ┌───────┴────────┐       ┌──────┴──────┐
      Local filesystem      ▼                ▼       ▼             ▼
                          SQLite         PostgreSQL  Rich        JSON file
            │                                      stderr
            │
            ▼
 .pyingest/runs / published

MetadataStore
      │
      └── runs / steps / artifacts metadata / validations / publications / events
```

---

# 48. Conclusion

La V0.1.x ne doit pas être considérée comme une simple version “pré-HTTP”. Elle constitue le **contrat de fondation** sur lequel reposeront tous les futurs jobs et packages PyIngestKit.

Le bon ordre est donc :

```text
STABILISER LES FONDATIONS
          ↓
FIGER LES CONTRATS
          ↓
FIGER LA DX
          ↓
FIGER LA PERSISTENCE
          ↓
FIGER L’OBSERVABILITÉ
          ↓
ENSUITE AJOUTER LES CAPACITÉS D’INGESTION
```

La cible recommandée est une **V0.1.5 “Foundation Consolidation”** suffisamment robuste pour que V0.2 puisse se concentrer exclusivement sur les capacités d’acquisition et de parsing, sans devoir rouvrir les décisions centrales du runtime.

Le garde-fou ultime reste :

> **PyIngestKit doit être excellent pour l’ingestion, pas moyen dans tous les domaines de la Data Platform.**

