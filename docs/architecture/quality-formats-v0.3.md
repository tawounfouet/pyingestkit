# PyIngestKit V0.3 — Quality & Formats Architecture & Implementation Plan

**Document:** `02_PYINGESTKIT_V0.3_QUALITY_FORMATS_ARCHITECTURE_IMPLEMENTATION_PLAN.md`  
**Target release:** `v0.3.0`  
**Milestone name:** **QUALITY & FORMATS**  
**Baseline:** `v0.2.0 — Acquisition Release`  
**Status:** Architecture & implementation plan — ready for execution  
**Date:** 2026-09-04

---

# 0. Résumé exécutif

PyIngestKit V0.2.0 a fermé le cycle **Acquisition** en livrant une chaîne fiable et installable allant de la source HTTP ou locale jusqu'au RAW immuable, au parsing CSV/JSON, au `Dataset`, au `DatasetContract`, à la validation runtime, au manifest, au `MetadataStore` et aux événements.

La V0.3 ne doit pas rouvrir cette plomberie. Elle doit construire **au-dessus** de ce socle stable afin de répondre à une question différente :

> **Comment caractériser, contrôler, rapporter et lire davantage de formats de données sans perdre les garanties de simplicité, de neutralité moteur et de traçabilité de PyIngestKit ?**

La V0.3 est donc structurée autour de quatre axes :

1. **Quality Contracts V2** — enrichir les contraintes génériques de `FieldContract` / `DatasetContract` sans introduire de règles métier ni de mutation des données ;
2. **Dataset Profiling** — produire des statistiques descriptives déterministes et engine-neutral sur un `Dataset` ;
3. **Quality Reports** — matérialiser validation et profiling sous forme d'artefacts de run reproductibles ;
4. **Formats supplémentaires** — ajouter NDJSON, Excel et Parquet sans faire de Pandas, Polars ou Arrow le modèle canonique du framework.

La signature architecturale V0.3 devient :

```text
External Source
      │
      ▼
Acquisition V0.2
      │
      ▼
RawArtifact
      │
      ▼
Parser
 ┌────┼───────────────┐
 ▼    ▼       ▼       ▼
CSV  JSON   NDJSON   Excel   Parquet
 └────┴───────┴───────┴──────┘
               │
               ▼
            Dataset
               │
       ┌───────┴────────┐
       ▼                ▼
DatasetContract V2   DatasetProfiler
       │                │
       ▼                ▼
ValidationResult     DatasetProfile
       └───────┬────────┘
               ▼
          QualityReport
               │
        ┌──────┼──────────┐
        ▼      ▼          ▼
     reports/ Manifest  Metadata/Events
```

La doctrine centrale reste inchangée :

```text
Dataset           ≠ Pandas / Polars / Arrow
Parser            ≠ Normalizer métier
Contract          ≠ Transformation
Profiler          ≠ Inférence métier
Quality Report    ≠ Data Catalog
PyIngestKit       ≠ Orchestrateur
```

La V0.3 sera livrée progressivement :

```text
V0.3.0-a1  Quality Contracts V2
V0.3.0-a2  Dataset Profiling + Quality Reports
V0.3.0-b1  NDJSON + Excel
V0.3.0-rc1  Parquet
V0.3.0-rc1 Quality & Formats E2E
V0.3.0     Quality & Formats Release
```

Le premier livrable d'implémentation sera :

```text
pyingestkit-v0.3.0-a1-quality-contracts.zip
```

---

# 1. Baseline officielle

## 1.1. V0.1.6 — Foundation Freeze

La Foundation reste gelée. Elle fournit notamment :

- `Job`, `Step`, `Pipeline`, `Runner` ;
- API déclarative `@job` / `@step` ;
- `ArtifactStore` ;
- `MetadataStore` SQLite / PostgreSQL ;
- manifest et provenance ;
- événements runtime ;
- CLI Typer + Rich ;
- plugin discovery ;
- logging structuré ;
- quality/security/build gates.

La V0.3 ne doit pas réinventer ces primitives.

## 1.2. V0.2.0 — Acquisition Release

La V0.2.0 est la baseline fonctionnelle immédiate :

```text
Local / HTTP
     │
     ▼
Source
     │
     ▼
RAW immutable + SHA-256 + provenance
     │
     ▼
CSV / JSON Parser
     │
     ▼
Dataset
     │
     ▼
DatasetContract
     │
     ▼
ValidationResult
     │
     ├── Manifest
     ├── MetadataStore
     └── Events
```

Les jobs de référence scellés en V0.2.0 sont :

```text
demo.local_file
demo.http_csv
demo.http_json
```

Leur non-régression est obligatoire pendant tout le cycle V0.3.

---

# 2. Mission de la V0.3

La V0.3 doit permettre à PyIngestKit de passer d'une ingestion structurée minimale à une ingestion **qualifiée et multi-format**, tout en gardant les couches distinctes.

La mission peut se résumer ainsi :

> **Lire plus de formats, mieux décrire les datasets et mieux qualifier leur conformité, sans transformer PyIngestKit en moteur dataframe, en plateforme de Data Quality ou en outil métier.**

La V0.3 doit renforcer le segment :

```text
PARSE → DESCRIBE → VALIDATE → REPORT
```

et non étendre agressivement :

```text
FETCH → CONNECTORS → ORCHESTRATION → TRANSFORMATION → BI
```

---

# 3. Objectifs fonctionnels

La V0.3 doit fournir :

- des contraintes de champ enrichies ;
- des contraintes multi-colonnes génériques ;
- une notion explicite de clé logique/clé de dataset ;
- un profiling déterministe ;
- des statistiques de qualité exploitables ;
- des rapports JSON de validation et profiling ;
- un parser NDJSON ;
- un parser Excel ;
- un parser Parquet optionnel ;
- des jobs de référence démontrant les nouveaux formats ;
- des tests offline et déterministes ;
- une compatibilité complète avec les vertical slices V0.2.0.

---

# 4. Objectifs techniques

La V0.3 doit préserver les propriétés suivantes :

- Python >= 3.11 ;
- typage strict Mypy ;
- Ruff lint + formatter ;
- Bandit ;
- `pip-audit` ;
- wheel/sdist ;
- smoke tests depuis wheels ;
- aucun effet de bord à l'import ;
- aucune dépendance dataframe obligatoire ;
- API publique explicite ;
- tests sans dépendance à Internet ;
- outputs machine-readable déterministes ;
- compatibilité avec la sérialisation manifest/metadata existante.

---

# 5. Objectifs d'expérience développeur

L'API doit rester lisible et composable.

Exemple cible :

```python
from pyingestkit import (
    CsvParser,
    DatasetContract,
    DatasetProfiler,
    FieldContract,
)

rows = CsvParser().parse(raw_artifact)

contract = DatasetContract(
    fields=(
        FieldContract(
            "postal_code",
            nullable=False,
            expected_type=str,
            pattern=r"^\d{5}$",
            min_length=5,
            max_length=5,
        ),
        FieldContract(
            "country",
            nullable=False,
            allowed_values={"FR"},
        ),
    ),
    primary_key=("postal_code", "commune_code"),
)

validation = contract.validate(rows)
profile = DatasetProfiler().profile(rows)
```

Le développeur doit pouvoir comprendre immédiatement :

```text
parse()     → structure les données
validate()  → vérifie sans muter
profile()   → décrit sans muter
normalize() → reste métier / job pack
```

---

# 6. Non-objectifs V0.3

La V0.3 n'implémente pas :

- Pandas comme type canonique ;
- Polars comme type canonique ;
- Arrow comme type canonique ;
- Spark ;
- DuckDB comme runtime obligatoire ;
- SQL transformation engine ;
- dataframe expression DSL ;
- JSONPath complet ;
- XPath complet ;
- XML ;
- Avro ;
- ORC ;
- streaming distribué ;
- chunk processing généralisé ;
- validation métier ;
- règles comptables/fiscales/référentielles métier ;
- ML anomaly detection ;
- schema registry externe ;
- Great Expectations-like DSL ;
- Data Catalog ;
- lineage platform ;
- scheduler ;
- async Runner ;
- multiprocessing framework ;
- orchestration DAG distribuée.

---

# 7. Garde-fou d'admission des fonctionnalités

Toute fonctionnalité proposée pendant V0.3 doit passer cinq questions :

1. Est-elle utile à plusieurs familles de jobs ?
2. Est-elle indépendante d'un domaine métier ?
3. Appartient-elle à `PARSE / QUALITY / REPORT` ?
4. Peut-elle rester indépendante d'un moteur dataframe ?
5. Réduit-elle réellement la plomberie répétitive des jobs ?

Si plusieurs réponses sont négatives :

```text
→ job pack
→ plugin spécialisé
→ outil externe
→ backlog post-V1
```

---

# 8. Architecture macro V0.3

```text
                         PYINGESTKIT V0.3

┌─────────────────────────────────────────────────────────────────────┐
│                         ACQUISITION V0.2                            │
│ Source → Retry → RAW → provenance                                  │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │ RawArtifact  │
                              └──────┬───────┘
                                     │
                 ┌───────────────────┼───────────────────────┐
                 ▼                   ▼                       ▼
           ┌──────────┐        ┌───────────┐           ┌───────────┐
           │ Text-like │        │ Workbook  │           │ Columnar  │
           │ parsers   │        │ parser    │           │ parser    │
           └────┬─────┘        └─────┬─────┘           └─────┬─────┘
                │                     │                       │
      CSV / JSON / NDJSON           Excel                  Parquet
                │                     │                       │
                └──────────────┬──────┴───────────────┬──────┘
                               ▼                      │
                         ┌──────────┐                 │
                         │ Dataset  │◄────────────────┘
                         └────┬─────┘
                              │
                ┌─────────────┴───────────────┐
                ▼                             ▼
       ┌─────────────────┐            ┌────────────────┐
       │ DatasetContract │            │ DatasetProfiler│
       │       V2        │            └────────┬───────┘
       └────────┬────────┘                     │
                ▼                              ▼
       ValidationResult                DatasetProfile
                │                              │
                └──────────────┬───────────────┘
                               ▼
                        ┌──────────────┐
                        │QualityReport │
                        └──────┬───────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
              reports/      Manifest       Events
```

---

# 9. Structure de packages cible

Ajouts proposés :

```text
src/pyingestkit/
├── contracts/
│   ├── dataset.py
│   ├── constraints.py          # nouveau
│   └── keys.py                 # possible, si séparation utile
├── parsers/
│   ├── base.py
│   ├── csv.py
│   ├── json.py
│   ├── ndjson.py               # nouveau
│   ├── excel.py                # nouveau
│   └── parquet.py              # nouveau
├── profiling/
│   ├── __init__.py
│   ├── models.py               # nouveau
│   └── profiler.py             # nouveau
├── quality/
│   ├── __init__.py
│   ├── report.py               # nouveau
│   └── writer.py               # nouveau
└── validation/
    ├── result.py
    ├── report.py
    └── rules.py
```

Le nom `profiling` est préféré à un package générique `analytics` afin de garder une responsabilité étroite.

Le nom `quality` doit rester réservé aux artefacts/synthèses de qualité, pas devenir un framework de règles parallèle à `contracts`.

---

# 10. Dependency policy V0.3

## 10.1. Principe

PyIngestKit doit continuer à utiliser des dépendances tierces matures lorsqu'elles évitent de réimplémenter des formats complexes, mais sans faire entrer des moteurs analytiques lourds dans le cœur par défaut.

## 10.2. NDJSON

Aucune dépendance supplémentaire :

```text
json stdlib
```

## 10.3. Excel

Dépendance recommandée :

```text
openpyxl
```

Sous extra optionnel :

```toml
[project.optional-dependencies]
excel = ["openpyxl>=3.1,<4"]
```

Raison : XLSX est un format non trivial ; le réimplémenter est hors scope.

## 10.4. Parquet

Dépendance recommandée :

```text
pyarrow
```

Sous extra optionnel :

```text
pyingestkit[parquet]
```

La borne exacte de version devra être figée pendant le jalon B2 après validation Python 3.11/3.12/3.13 et wheel availability.

## 10.5. Interdiction de dépendance implicite

Aucune de ces dépendances ne doit être importée au chargement du package principal si l'extra n'est pas installé.

Un utilisateur qui n'utilise ni Excel ni Parquet doit pouvoir installer :

```bash
pip install pyingestkit
```

sans `openpyxl` ni `pyarrow`.

---

# 11. Dataset reste le contrat pivot

Le `Dataset` V0.2 est conservé comme frontière framework-owned :

```text
Sequence[Mapping[str, Any]]
+ ordered fields
+ source_artifact_id
```

La V0.3 ne doit pas le transformer en dataframe universel.

---

# 12. Dataset ≠ DataFrame

Le contrat reste explicitement :

```text
Dataset
≠ pandas.DataFrame
≠ polars.DataFrame
≠ pyarrow.Table
```

Ces technologies pourront être utilisées dans des adapters explicites plus tard, mais elles ne déterminent pas la sémantique centrale de PyIngestKit.

---

# 13. Limite de matérialisation mémoire

Le Dataset V0.2 est matérialisé en mémoire.

Ceci reste acceptable pour V0.3 mais doit être documenté comme une limite :

```text
RAW 50 MB  → probablement acceptable selon structure
RAW 3 GB   → potentiellement non acceptable en Dataset matérialisé
```

La V0.3 ne doit pas masquer cette réalité.

Le design doit cependant éviter de rendre impossible une future abstraction :

```text
Dataset
BufferedDataset
StreamingDataset
```

Aucun de ces deux derniers types n'est requis en V0.3.

---

# 14. Quality Contracts V2 — responsabilité

Le `DatasetContract` V2 décrit des attentes génériques vérifiables sur la structure et les valeurs observées d'un dataset.

Il ne doit :

- ni modifier les lignes ;
- ni remplir les valeurs manquantes ;
- ni caster silencieusement ;
- ni appeler des services externes ;
- ni appliquer des nomenclatures métier ;
- ni enrichir les données.

---

# 15. FieldContract V2

API cible indicative :

```python
FieldContract(
    name="postal_code",
    required=True,
    nullable=False,
    expected_type=str,
    unique=False,
    allowed_values=None,
    pattern=r"^\d{5}$",
    min_value=None,
    max_value=None,
    min_length=5,
    max_length=5,
)
```

---

# 16. `allowed_values`

La contrainte doit vérifier l'appartenance exacte à un ensemble fini :

```python
FieldContract(
    "country_code",
    allowed_values={"FR", "BE", "CH"},
)
```

Sémantique :

```text
null + nullable=True      → pas d'échec allowed_values
null + nullable=False     → erreur nullability
value hors ensemble       → erreur field.allowed_values
```

---

# 17. `pattern`

La contrainte regex s'applique uniquement aux valeurs chaînes.

Exemple :

```python
FieldContract(
    "postal_code",
    expected_type=str,
    pattern=r"^\d{5}$",
)
```

Décision : `re.fullmatch` est préférable à un `search` implicite afin que le contrat soit non ambigu.

---

# 18. `min_value` / `max_value`

Contraintes génériques sur des valeurs comparables :

```python
FieldContract("age", min_value=0, max_value=130)
```

Le moteur ne doit pas convertir une chaîne CSV `"42"` en entier pour satisfaire la contrainte.

Si le type observé n'est pas compatible avec la comparaison, le résultat doit être un issue explicite et déterministe, pas une exception non contrôlée.

---

# 19. `min_length` / `max_length`

Applicable aux valeurs pour lesquelles une longueur est définie de façon sûre, principalement chaînes et collections supportées.

V0.3-a1 peut choisir de limiter explicitement le comportement aux chaînes pour éviter une sémantique trop large.

---

# 20. Required vs nullable

Les concepts restent distincts :

```text
required=False
→ le champ peut être absent du schéma / de la ligne selon contrat

nullable=True
→ le champ présent peut contenir None
```

Le framework doit éviter de confondre :

```text
missing field
null value
empty string
```

Ces trois états sont distincts.

---

# 21. Unicité simple

Le comportement `unique=True` existant est conservé et renforcé avec des issues cohérents.

L'identité des doublons doit être signalable par `row_index`.

---

# 22. Unicité composite

Nouvelle contrainte dataset-level :

```python
DatasetContract(
    ...,
    unique_together=(
        ("country", "postal_code"),
        ("source", "external_id"),
    ),
)
```

Ou API simplifiée :

```python
composite_unique=(("country", "postal_code"),)
```

Le nom final doit être choisi une fois et gelé en Alpha 1.

---

# 23. Primary key / business key

La V0.3 introduit une notion de clé déclarative purement technique :

```python
primary_key=("country", "postal_code")
```

Sémantique minimale :

- champs présents ;
- valeurs non nulles ;
- combinaison unique.

Le terme `primary_key` est acceptable comme clé logique de dataset mais doit être documenté : ce n'est pas une contrainte de base de données ni un mécanisme de persistence SQL.

Alternative plus neutre possible :

```text
key_fields
```

Décision à prendre dans ADR-028.

---

# 24. ValidationIssue V2

Le modèle doit rester compact mais devenir plus exploitable.

Champs cibles :

```text
code
message
severity
field
row_index
value_preview       # optionnel, redacted/tronqué
constraint          # optionnel
context             # mapping JSON-safe optionnel
```

Le framework ne doit jamais mettre une valeur potentiellement secrète ou énorme en clair dans `value_preview`.

---

# 25. Codes d'issues stables

Convention cible :

```text
dataset.required_field
dataset.extra_field
dataset.row_count.min
dataset.row_count.max
dataset.unique_together
field.null
field.type
field.unique
field.allowed_values
field.pattern
field.min_value
field.max_value
field.min_length
field.max_length
key.null
key.duplicate
```

Ces codes sont plus importants pour les consommateurs machine que les messages humains.

---

# 26. Severity

Les niveaux V0.2 restent :

```text
ERROR
WARNING
REVIEW
```

Une contrainte contractuelle standard produit `ERROR` par défaut.

La V0.3 ne doit pas introduire une hiérarchie complexe de severity tant qu'un besoin concret ne l'exige pas.

---

# 27. Issue limit

Pour éviter un rapport de millions de lignes :

```python
DatasetContract(..., max_issues=1000)
```

ou paramètre de validation :

```python
contract.validate(dataset, max_issues=1000)
```

Le design doit signaler explicitement si le résultat a été tronqué :

```text
issues_truncated = true
```

---

# 28. Fail-fast vs collect-all

Par défaut :

```text
collect-all jusqu'à max_issues
```

Le fail-fast ne doit pas être la sémantique par défaut car il réduit la valeur diagnostique des rapports.

Une option future pourra exister, mais elle n'est pas prioritaire en V0.3-a1.

---

# 29. Validation ≠ coercion

Exemple :

```text
CSV value = "42"
expected_type = int
```

Résultat :

```text
field.type ERROR
```

et non :

```text
"42" → 42
```

La conversion appartient à une étape de normalisation explicite du job pack.

---

# 30. Validation ≠ normalisation métier

Exemples hors scope :

```text
"FRANCE" → "FR"
"75001 PARIS" → postal_code=75001
SIREN checksum
IBAN validation métier approfondie
réconciliation avec référentiel INSEE
mapping statut client
```

Ces règles sont des règles de job pack, même si elles sont réutilisées par plusieurs jobs du même domaine.

---

# 31. DatasetProfiler — responsabilité

Le profiler doit répondre à :

> **Quelles caractéristiques descriptives observons-nous dans ce Dataset ?**

Il ne répond pas à :

> **Que signifient ces valeurs métier ?**

---

# 32. DatasetProfile

Modèle cible :

```text
DatasetProfile
├── row_count
├── field_count
├── fields
│   └── FieldProfile[]
├── duplicate_row_count
├── source_artifact_id
├── generated_at
└── duration_ms
```

---

# 33. FieldProfile

Modèle cible :

```text
FieldProfile
├── name
├── present_count
├── null_count
├── non_null_count
├── distinct_count
├── observed_types
├── min_length
├── max_length
├── min_value        # si comparable et sûr
├── max_value        # si comparable et sûr
└── sample_values    # optionnel, limité/redacted
```

---

# 34. Observed types

Le profiler doit décrire les types Python observés :

```text
str
int
float
bool
datetime
NoneType
...
```

Il ne doit pas faire une inférence sémantique agressive comme :

```text
"2026-09-04" → date
"00123"      → integer
```

notamment parce que le CSV V0.2 préserve volontairement les chaînes.

---

# 35. Distinct count

Le comptage distinct doit être exact en V0.3 pour les Datasets matérialisés.

Les algorithmes probabilistes type HyperLogLog sont hors scope.

---

# 36. Duplicate row count

Le profiler peut compter les doublons de ligne complète lorsque les valeurs sont hashables / normalisables de façon sûre.

Pour les structures imbriquées JSON non hashables, il faut soit :

- utiliser une canonicalisation JSON déterministe ;
- soit signaler la métrique indisponible.

La simplicité et la déterminisme priment.

---

# 37. Min/max numériques

Le profiler peut calculer min/max si toutes les valeurs non nulles d'un champ sont mutuellement comparables.

Il ne doit pas lever une exception si un champ contient des types hétérogènes.

---

# 38. String length profile

Pour les champs de chaînes :

```text
min_length
max_length
```

Éventuellement `avg_length` peut être ajouté si le coût reste trivial.

---

# 39. Profiling et confidentialité

Par défaut, aucun échantillon de valeurs n'est nécessaire.

Si `sample_values` est retenu :

- limite faible ;
- troncature ;
- pas de collecte de champs secrets identifiés ;
- désactivable ;
- jamais de contenu RAW volumineux.

La V0.3-a2 peut préférer **ne pas inclure de sample values du tout** afin de garder la surface sûre.

---

# 40. Determinism du profiler

Même input → même résultat métier, hors timestamps/duration.

L'ordre des champs doit suivre `Dataset.fields`.

Les types observés doivent avoir un ordre stable.

---

# 41. DatasetProfiler API

Proposition :

```python
profile = DatasetProfiler().profile(dataset)
```

Alternative fonctionnelle :

```python
profile_dataset(dataset)
```

Préférence V0.3 : objet `DatasetProfiler`, car il permet des options explicites sans gonfler `Dataset` lui-même.

---

# 42. Pourquoi ne pas ajouter `dataset.profile()`

Le `Dataset` doit rester un conteneur simple.

Placer profiling, validation, conversion et export directement sur `Dataset` créerait progressivement un mini-dataframe.

Donc :

```text
Dataset = données
DatasetProfiler = comportement de profiling
DatasetContract = comportement de validation
```

---

# 43. QualityReport — objectif

La V0.3 doit matérialiser un résultat qualité stable et portable.

Un report agrège :

```text
validation
profiling
identité du dataset
provenance du RAW
résumé exécution
```

sans dupliquer inutilement toutes les données.

---

# 44. QualityReport model

Proposition :

```text
QualityReport
├── report_version
├── run_id
├── job_id
├── dataset_ref
├── source_artifact_id
├── generated_at
├── validation
└── profile
```

`validation` ou `profile` peuvent être optionnels selon le job.

---

# 45. Artefact `quality.json`

Chemin recommandé :

```text
.pyingest/
└── runs/<namespace>/<job>/<run-id>/
    └── reports/
        ├── validation.json
        ├── profile.json
        └── quality.json       # agrégat facultatif / RC
```

La V0.3-a2 peut commencer par :

```text
validation.json
profile.json
```

et n'ajouter `quality.json` que si l'agrégation apporte une valeur réelle.

---

# 46. JSON comme format canonique de report

Le report machine-readable canonique est JSON.

Pas de HTML obligatoire en V0.3.

Pas de PDF.

Pas de Markdown généré automatiquement comme format canonique.

---

# 47. Rendu terminal

Rich peut afficher un résumé humain :

```text
Quality summary
───────────────
Rows              39,847
Fields                 8
Validation         PASSED
Errors                  0
Warnings                2
Duplicate rows          0
```

Le rendu terminal est une vue, pas la source de vérité.

---

# 48. Manifest integration

Le manifest doit référencer les artefacts qualité sans embarquer arbitrairement leur contenu complet si celui-ci devient volumineux.

Approche recommandée :

```json
{
  "reports": [
    {
      "kind": "validation",
      "path": "reports/validation.json"
    },
    {
      "kind": "profile",
      "path": "reports/profile.json"
    }
  ]
}
```

La structure exacte doit rester additive et backward-compatible.

---

# 49. MetadataStore impact

Objectif V0.3 : **éviter une migration SQL structurante si possible**.

Les validations structurées utilisent déjà `MetadataStore`.

Le profiling peut rester :

```text
artifact report + manifest + event
```

sans créer immédiatement des tables relationnelles `profiles` / `field_profiles`.

La relationalisation pourra être reconsidérée si un vrai besoin de requêtage historique apparaît.

---

# 50. Alembic guardrail

La V0.3 ne doit pas introduire Alembic uniquement pour stocker des profils.

La règle ADR-021 reste : migration framework seulement lorsqu'un besoin de migration de schéma publié est démontré.

---

# 51. Runtime events V0.3

Événements additifs possibles :

```text
PROFILE_STARTED
PROFILE_COMPLETED
QUALITY_REPORT_WRITTEN
```

Ne pas créer un événement par champ ou par règle : le volume serait inutilement élevé.

---

# 52. Metrics V0.3

Métriques candidates :

```text
dataset.row_count
dataset.field_count
validation.issue_count
validation.error_count
validation.warning_count
profile.duplicate_row_count
profile.duration_ms
```

Elles doivent rester petites, numériques, structurées et stables.

---

# 53. NDJSON Parser — responsabilité

NDJSON / JSON Lines contient un document JSON par ligne :

```text
{"id": 1, "name": "A"}
{"id": 2, "name": "B"}
{"id": 3, "name": "C"}
```

`NdjsonParser` transforme ces objets en `Dataset` sans normalisation métier.

---

# 54. API NDJSON cible

```python
parser = NdjsonParser(
    encoding="utf-8",
    skip_blank_lines=True,
)

dataset = parser.parse(raw_artifact)
```

---

# 55. Sémantique NDJSON

Chaque ligne non vide doit être :

```text
JSON object
```

Un tableau, scalar ou null top-level doit produire `ParseError` avec numéro de ligne.

---

# 56. Erreurs NDJSON

Exemple :

```text
Invalid NDJSON payload at line 42
```

Le message ne doit pas reproduire une ligne potentiellement sensible en entier.

---

# 57. NDJSON et mémoire

V0.3-b1 peut parser ligne par ligne mais matérialise finalement un `Dataset`.

Cette structure prépare le futur streaming sans le promettre.

---

# 58. Excel Parser — responsabilité

`ExcelParser` lit un workbook XLSX et extrait une feuille tabulaire en `Dataset`.

Il ne doit pas essayer de reproduire Excel comme application.

---

# 59. Formats Excel supportés

V0.3 vise :

```text
.xlsx
```

Pas :

```text
.xls legacy
.xlsb
.ods
macro execution
Power Query
formulas recalculation engine
```

---

# 60. API Excel cible

```python
parser = ExcelParser(
    sheet="Communes",
    header_row=1,
    skip_empty_rows=True,
)

dataset = parser.parse(raw_artifact)
```

Sélection possible :

```text
sheet name
ou sheet index
```

mais pas les deux simultanément.

---

# 61. Excel header semantics

Le header doit être explicite :

```text
header_row=1
```

V0.3 n'essaie pas de détecter automatiquement une ligne de header dans un classeur arbitraire.

---

# 62. Excel duplicate headers

Les headers dupliqués doivent produire `ParseError` plutôt qu'un renommage silencieux :

```text
name, name
```

ne devient pas :

```text
name, name_2
```

---

# 63. Excel cell types

Contrairement au CSV, Excel possède des types de cellule.

Le parser doit préserver les valeurs Python fournies de façon sûre par `openpyxl` :

```text
str
int
float
bool
datetime/date
None
```

Pas de normalisation métier supplémentaire.

---

# 64. Excel formulas

Décision recommandée V0.3 :

```text
data_only=True
```

pour lire les valeurs calculées/cachées lorsque présentes, sans exécuter de moteur de formule.

Le comportement doit être documenté clairement.

---

# 65. Excel merged cells

Les merged cells et mises en page complexes sont hors du cas tabulaire simple.

Le parser ne doit pas inventer une logique de propagation métier.

---

# 66. Excel workbook security

Le framework ne doit exécuter :

- aucune macro ;
- aucun code embarqué ;
- aucun lien externe ;
- aucune formule active.

---

# 67. Excel optional dependency error

Si `openpyxl` n'est pas installé :

```text
ConfigurationError / ParseError dédié
```

avec message utile :

```text
Excel support requires the 'excel' extra: pip install 'pyingestkit[excel]'
```

Pas d'`ImportError` brut exposé à l'utilisateur.

---

# 68. Parquet Parser — responsabilité

Le parser Parquet lit un fichier colonne et le convertit vers le contrat `Dataset` du framework.

Il ne transforme pas `Dataset` en façade Arrow.

---

# 69. Parquet dependency boundary

`pyarrow` est utilisé comme moteur technique du parser uniquement.

```text
RawArtifact
   ↓
PyArrow adapter (internal)
   ↓
Dataset
```

Pas :

```text
Dataset == pyarrow.Table
```

---

# 70. API Parquet cible

```python
parser = ParquetParser(
    columns=None,
)

dataset = parser.parse(raw_artifact)
```

Projection optionnelle de colonnes peut être acceptée car elle appartient au format et peut réduire fortement la mémoire.

---

# 71. Parquet row groups

La V0.3-b2 peut utiliser les primitives PyArrow de lecture optimisée, mais le résultat final reste matérialisé.

Le streaming row-group généralisé est différé.

---

# 72. Parquet nested structures

Les colonnes imbriquées doivent être traitées prudemment.

V0.3 peut :

- préserver listes/dicts Python lorsqu'ils sont convertibles ;
- documenter les limites ;
- refuser certaines structures complexes avec `ParseError` clair.

Pas de flattening automatique.

---

# 73. Parquet timestamps / decimals

Les types riches doivent être convertis vers des objets Python stables quand possible :

```text
datetime
Decimal
bytes
list
dict
```

Le profiler doit tolérer ces types même s'il ne sait pas calculer toutes les métriques dessus.

---

# 74. Parquet optional dependency error

Message explicite :

```text
Parquet support requires the 'parquet' extra: pip install 'pyingestkit[parquet]'
```

---

# 75. Parser ≠ normalizer — rappel multi-format

Exemples interdits dans les parsers :

```text
trim automatique
uppercase
mapping de codes
renommage métier
conversion "001" → 1
remplacement vide → None selon métier
correction d'encodage heuristique agressive
jointure avec référentiel
```

---

# 76. Parser configuration

Les options parser doivent être techniques et déterministes :

```text
encoding
delimiter
sheet
header_row
records_path
columns
skip_blank_lines
```

Pas :

```text
map_country_codes
normalize_company_name
fix_siren
```

---

# 77. Format detection

V0.3 ne doit pas introduire un auto-détecteur universel de format.

Le job sait généralement ce qu'il ingère.

L'extension ou le content-type peuvent être utilisés comme aide, pas comme magie implicite.

---

# 78. MIME types

MIME utiles :

```text
application/json
application/x-ndjson
text/csv
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
application/vnd.apache.parquet
```

Mais la sélection du parser reste explicite dans le job.

---

# 79. Quality report writer

Responsabilité :

```text
model Python
   ↓
JSON-safe normalization
   ↓
ArtifactStore.write_json(... reports/...)
```

Le writer ne doit pas modifier validation/profile.

---

# 80. JSON-safe serialization

Doit supporter proprement :

```text
datetime → ISO-8601
Decimal  → string ou convention documentée
set      → sorted list si utilisé
Enum     → value
```

La représentation doit être stable.

---

# 81. Report schema version

Ajouter :

```json
"report_version": "1"
```

afin de permettre l'évolution future sans ambiguïté.

---

# 82. Quality status global

Une synthèse simple :

```text
PASSED
FAILED
REVIEW
```

peut être dérivée de `ValidationResult`.

Le profiling seul ne doit pas produire artificiellement un statut de conformité.

---

# 83. CLI impact

La V0.3 doit minimiser les nouveaux sous-commandes.

Priorité : enrichir :

```text
pyingest status <run>
```

avec :

```text
validation summary
quality report paths
profile summary si présent
```

---

# 84. CLI JSON impact

`status --json` doit continuer à être stable et non décoré.

Les nouveaux champs doivent être additifs.

---

# 85. Pas de CLI `profile file.xlsx` générique en V0.3

Une telle commande contournerait le lifecycle job/run/provenance et créerait une seconde surface d'exécution.

Le profiling doit d'abord rester une étape de pipeline.

---

# 86. Jobs de référence V0.3

Jobs proposés :

```text
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

Le RC peut garder les trois jobs V0.2 et ajouter ces trois jobs.

---

# 87. `demo.ndjson_quality`

Vertical slice :

```text
fixture RAW NDJSON
      ↓
NdjsonParser
      ↓
Dataset
      ↓
DatasetContract V2
      ↓
DatasetProfiler
      ↓
reports/validation.json
reports/profile.json
```

---

# 88. `demo.excel_quality`

Vertical slice :

```text
fixture XLSX
      ↓
ExcelParser
      ↓
Dataset
      ↓
Contract
      ↓
Profile
      ↓
Quality reports
```

Le test doit fonctionner sans réseau.

---

# 89. `demo.parquet_quality`

Vertical slice :

```text
fixture Parquet
      ↓
ParquetParser
      ↓
Dataset
      ↓
Contract
      ↓
Profile
      ↓
Quality reports
```

Le test est conditionné à l'extra `parquet` dans les gates qui l'installent.

---

# 90. Demo plugin versioning

Le demo pack doit évoluer en parallèle :

```text
pyingestkit-demo-jobs 0.3.0
```

pour la release stable V0.3.0.

Les versions alpha/beta du pack peuvent suivre le framework si cela simplifie les wheel smoke tests.

---

# 91. Tests 100 % offline

Aucun test V0.3 ne doit dépendre :

- d'un endpoint externe ;
- d'un CDN ;
- d'un fichier téléchargé au runtime ;
- d'un API public ;
- d'une base distante.

Les fixtures Excel/Parquet doivent être versionnées comme petites fixtures de test ou générées localement de manière déterministe.

---

# 92. Fixtures binaires

Pour Excel/Parquet :

- petites ;
- reproductibles ;
- non sensibles ;
- hashables ;
- documentées.

On peut aussi générer les fixtures dans les tests via `openpyxl`/`pyarrow` afin d'éviter des blobs opaques trop nombreux.

---

# 93. Contract tests V0.3

Les tests contractuels doivent vérifier :

```text
public API
no dataframe core dependencies
optional dependencies remain optional
parser boundaries
quality models JSON-safe
demo entry points stable
no import side effects
```

---

# 94. Dataset contract tests

Cas obligatoires :

- allowed values pass/fail ;
- regex pass/fail ;
- min/max pass/fail ;
- length pass/fail ;
- null behavior ;
- wrong type without coercion ;
- composite uniqueness ;
- key null ;
- key duplicate ;
- max issues ;
- deterministic issue ordering.

---

# 95. Profiling tests

Cas obligatoires :

- empty dataset ;
- one row ;
- null-only field ;
- mixed types ;
- strings ;
- numerics ;
- nested JSON values ;
- duplicate rows ;
- deterministic field order ;
- source artifact propagation.

---

# 96. NDJSON tests

Cas :

- valid records ;
- blank lines ;
- malformed line ;
- scalar line ;
- array line ;
- encoding error ;
- source artifact linkage.

---

# 97. Excel tests

Cas :

- sheet by name ;
- sheet by index ;
- missing sheet ;
- header row ;
- duplicate headers ;
- empty rows ;
- booleans/numbers/dates ;
- missing optional dependency ;
- formulas behavior documented.

---

# 98. Parquet tests

Cas :

- simple table ;
- column projection ;
- nulls ;
- timestamp ;
- decimal ;
- nested list/dict if supported ;
- invalid file ;
- missing optional dependency.

---

# 99. Quality report tests

Vérifier :

- chemins `reports/` ;
- JSON valide ;
- version schema ;
- timestamps ISO ;
- validation summary ;
- profile summary ;
- absence de données RAW complètes ;
- absence de secrets connus ;
- manifest references.

---

# 100. Backward compatibility

La V0.3 doit garantir :

```text
demo.local_file   ✅
demo.http_csv     ✅
demo.http_json    ✅
```

et les APIs V0.2 existantes :

```text
Dataset
CsvParser
JsonParser
FieldContract
DatasetContract
ValidationIssue
ValidationResult
HttpSource
RetryPolicy
```

ne doivent pas être cassées sans raison majeure.

---

# 101. Public API V0.3

Exports candidats :

```python
from pyingestkit import (
    DatasetProfiler,
    DatasetProfile,
    FieldProfile,
    NdjsonParser,
    ExcelParser,
    ParquetParser,
    QualityReport,
)
```

Les classes dépendant d'extras doivent pouvoir être importées sans charger immédiatement la dépendance tierce, ou être exportées via namespace avec import lazy sûr.

---

# 102. Optional import strategy

Exemple :

```python
class ExcelParser(Parser):
    def parse(...):
        try:
            import openpyxl
        except ImportError as exc:
            raise ConfigurationError(...)
```

Le module principal peut rester importable sans l'extra.

---

# 103. Exception hierarchy

Réutiliser :

```text
ParseError
ValidationError
ConfigurationError
StorageError
```

Ne pas créer une exception par format sauf besoin réel.

---

# 104. Error messages

Doivent être :

- actionnables ;
- sans secrets ;
- sans dump RAW ;
- avec line/sheet/column lorsque pertinent ;
- déterministes pour les tests.

---

# 105. Security — spreadsheets

Risques principaux :

```text
formulas
external links
macros
zip bombs / huge workbooks
resource exhaustion
```

Le parser ne doit exécuter aucun contenu actif.

---

# 106. Security — Parquet

Risques :

```text
resource exhaustion
crafted metadata
oversized nested values
```

Le parser s'appuie sur une bibliothèque mature et maintenue ; aucune implémentation binaire maison.

---

# 107. Resource limits

V0.3 doit documenter la mémoire matérialisée.

Des garde-fous simples peuvent être envisagés :

```text
max_rows
max_columns
```

mais ne doivent pas devenir des defaults arbitraires qui cassent des datasets réels.

---

# 108. Profiling cost

Certaines métriques sont O(n) mémoire/temps.

Distinct exact et duplicate exact peuvent être coûteux.

Le profiler doit rester clair sur ce coût ; pas de magie de performance.

---

# 109. Mode de profiling

V0.3 peut introduire :

```text
basic
```

comme seul mode officiel.

Des modes `deep` / `sampled` sont différés tant qu'un besoin concret n'existe pas.

---

# 110. Serialization stability

Les nouveaux dataclasses doivent fournir :

```text
as_dict()
```

ou un utilitaire de sérialisation unique, afin d'éviter des conversions ad hoc multiples.

---

# 111. Dataclasses vs Pydantic

Préférence :

- contrats de config utilisateur → Pydantic si nécessaire ;
- records runtime/domain → dataclasses/plain models, cohérent avec la Foundation.

Ne pas convertir toute la couche qualité en modèles Pydantic sans besoin.

---

# 112. Configuration YAML

La V0.3 ne doit pas forcer les contracts complexes en YAML.

Les contracts peuvent rester en code Python pour garder typage et composabilité.

---

# 113. Déclaratif contract en YAML — différé

Un DSL YAML de validation riche serait une fonctionnalité produit majeure et risque de devenir un mini Great Expectations.

Donc différé.

---

# 114. Documentation V0.3 à créer

Proposition :

```text
docs/architecture/quality-formats-v0.3.md
docs/guides/dataset-contracts-v2.md
docs/guides/dataset-profiling.md
docs/guides/parsing-ndjson.md
docs/guides/parsing-excel.md
docs/guides/parsing-parquet.md
docs/guides/quality-reports.md
```

---

# 115. ADRs V0.3 à créer

## ADR-028 — Dataset Contracts V2 semantics

Décider :

- contraintes supportées ;
- absence de coercion ;
- clés composites ;
- issue codes.

## ADR-029 — Dataset profiling is descriptive, not semantic inference

Décider :

- métriques de base ;
- observed types ;
- no semantic coercion.

## ADR-030 — Quality reports are run artifacts

Décider :

- `reports/*.json` ;
- manifest references ;
- pas de tables SQL de profiling en V0.3.

## ADR-031 — NDJSON parser contract

Décider :

- one object per line ;
- no JSONPath ;
- deterministic line errors.

## ADR-032 — Excel parser uses optional openpyxl adapter

Décider :

- `.xlsx` only ;
- no macros/formula execution ;
- optional extra.

## ADR-033 — Parquet parser uses optional PyArrow adapter

Décider :

- optional extra ;
- Dataset remains canonical ;
- projection support.

## ADR-034 — Materialized Dataset boundary and future streaming compatibility

Décider :

- V0.3 stays materialized ;
- future streaming not blocked.

---

# 116. Git workflow V0.3

Branche de cycle :

```text
feat/v0.3-quality-formats
```

Chaque milestone peut être une PR ou une série de commits cohérents sur cette branche, mais chaque ZIP intermédiaire doit correspondre à un HEAD CI vert.

---

# 117. Versioning V0.3

PEP 440 package versions :

```text
0.3.0a1
0.3.0a2
0.3.0b1
0.3.0
0.3.0
0.3.0
```

Noms documentaires ZIP :

```text
pyingestkit-v0.3.0-a1-quality-contracts.zip
pyingestkit-v0.3.0-a2-profiling-reports.zip
pyingestkit-v0.3.0-b1-ndjson-excel.zip
pyingestkit-v0.3.0-rc1-parquet.zip
pyingestkit-v0.3.0-rc1-quality-formats-e2e.zip
pyingestkit-v0.3.0.zip
```

---

# 118. Milestone A1 — Quality Contracts V2

Livrable :

```text
pyingestkit-v0.3.0-a1-quality-contracts.zip
```

Contenu :

```text
FieldContract V2
DatasetContract V2
allowed_values
pattern
min/max
min/max length
composite uniqueness
logical key
richer ValidationIssue
issue codes
issue limit
```

Sans :

```text
profiling
Excel
Parquet
NDJSON
new persistence schema
```

---

# 119. DoD A1

A1 est terminé si :

- toutes les contraintes sont unit-testées ;
- validation ne mute jamais Dataset ;
- aucune coercion implicite ;
- issues déterministes ;
- API V0.2 compatible ;
- `make verify` vert ;
- wheel smoke V0.2 non régressé ;
- ZIP propre.

---

# 120. Milestone A2 — Dataset Profiling + Quality Reports

Livrable :

```text
pyingestkit-v0.3.0-a2-profiling-reports.zip
```

Contenu :

```text
DatasetProfiler
DatasetProfile
FieldProfile
profile.json
validation.json
manifest report references
PROFILE_COMPLETED event
status CLI summary
```

---

# 121. DoD A2

- profiling deterministic ;
- mixed types handled safely ;
- no semantic inference ;
- no secrets/RAW dumps ;
- reports JSON versioned ;
- no SQL migration required ;
- `make verify` vert ;
- reports visible dans run workspace.

---

# 122. Milestone B1 — NDJSON + Excel

Livrable :

```text
pyingestkit-v0.3.0-b1-ndjson-excel.zip
```

Contenu :

```text
NdjsonParser
ExcelParser
optional extra [excel]
demo.ndjson_quality
demo.excel_quality
offline fixtures
```

---

# 123. DoD B1

- NDJSON line errors propres ;
- Excel `.xlsx` seulement ;
- openpyxl optional ;
- no macro execution ;
- headers stricts ;
- source artifact lineage conservée ;
- quality reports intégrés ;
- tests 100 % offline ;
- `make verify` vert.

---

# 124. Milestone B2 — Parquet

Livrable :

```text
pyingestkit-v0.3.0-rc1-parquet.zip
```

Contenu :

```text
ParquetParser
optional extra [parquet]
PyArrow internal adapter
column projection
demo.parquet_quality
```

---

# 125. DoD B2

- base Parquet roundtrip ;
- optional dependency isolation ;
- Python 3.11/3.12/3.13 wheels available ;
- Dataset remains canonical ;
- projection testée ;
- nested values behavior documenté ;
- no streaming promise ;
- `make verify` vert avec matrice appropriée.

---

# 126. Milestone RC1 — Quality & Formats E2E

Livrable :

```text
pyingestkit-v0.3.0-rc1-quality-formats-e2e.zip
```

Le RC doit démontrer :

```text
demo.local_file       ✅
demo.http_csv         ✅
demo.http_json        ✅
demo.ndjson_quality   ✅
demo.excel_quality    ✅
demo.parquet_quality  ✅
```

---

# 127. Vertical slice RC1

```text
HttpSource / LocalSource
        ↓
       RAW
        ↓
Parser (CSV/JSON/NDJSON/Excel/Parquet)
        ↓
Dataset
        ↓
DatasetContract V2
        ↓
ValidationResult
        ↓
DatasetProfiler
        ↓
DatasetProfile
        ↓
Quality Reports
        ↓
Manifest / Metadata / Events
```

---

# 128. Release V0.3.0

Livrables :

```text
pyingestkit-v0.3.0.zip
pyingestkit-0.3.0.tar.gz
pyingestkit-0.3.0-py3-none-any.whl
pyingestkit_demo_jobs-0.3.0.tar.gz
pyingestkit_demo_jobs-0.3.0-py3-none-any.whl
SHA256SUMS-v0.3.0.txt
```

Éventuellement :

```text
pyingestkit-v0.3.0-validation-evidence.zip
```

selon la pratique établie en V0.2.

---

# 129. Release gates V0.3

Le minimum reste :

```bash
make quality
make security
make verify
make build
make wheel-smoke
make release-check
```

Le gate doit installer les extras nécessaires pour les tests Excel/Parquet dans les jobs qui les exercent.

---

# 130. Matrix CI

Base :

```text
Python 3.11
Python 3.12
Python 3.13
```

Pour Parquet, la CI doit confirmer la disponibilité des wheels PyArrow sur les trois versions cibles.

Si une incompatibilité upstream réelle existe, elle doit être documentée explicitement plutôt que masquée.

---

# 131. Build extras smoke tests

Ajouter des smoke tests :

```text
base wheel only
wheel + excel extra
wheel + parquet extra
wheel + demo pack
```

L'objectif est de prouver que les extras ne contaminent pas l'installation minimale.

---

# 132. Source ZIP cleanliness

Comme V0.2 : exclure :

```text
.venv/
.pyingest/
.pytest_cache/
.mypy_cache/
.ruff_cache/
__pycache__/
build/
dist/
*.egg-info/
*.pyc
*.pyo
```

---

# 133. Changelog V0.3

Chaque milestone doit écrire une section distincte dans `CHANGELOG.md`.

La release stable résume :

```text
Quality Contracts V2
Dataset Profiling
Quality Reports
NDJSON
Excel
Parquet
```

---

# 134. README V0.3

Le README doit présenter les nouvelles capacités sans devenir un manuel exhaustif.

Sections :

```text
Quality contracts
Profiling
NDJSON / Excel / Parquet
Optional extras
Reference jobs
```

Les détails restent dans `docs/guides`.

---

# 135. Performance baseline

La V0.3 ne vise pas un benchmark engine-level, mais doit éviter les régressions manifestes.

Mesures simples possibles :

```text
profiling 10k rows
validation 10k rows
NDJSON parse 10k rows
```

Pas de promesse de SLA publique avant V1.

---

# 136. Profiling complexity budget

Les calculs par défaut doivent idéalement rester O(n) temps.

Mémoire additionnelle :

- distinct set : O(k) ;
- duplicate tracking : O(n) worst case.

Ces coûts doivent être documentés.

---

# 137. Future streaming compatibility

V0.3 doit éviter les APIs qui exigent définitivement :

```python
len(dataset.rows)
```

partout dans les contrats futurs.

Cependant, optimiser pour un streaming non implémenté ne doit pas complexifier les APIs actuelles.

---

# 138. Future adapters

Possibles plus tard :

```text
Dataset ↔ pandas
Dataset ↔ polars
Dataset ↔ pyarrow
```

Ils n'appartiennent pas au cœur V0.3 sauf besoin démontré.

---

# 139. Future formats différés

Backlog :

```text
XML
Avro
ORC
Fixed-width
ZIP multi-entry datasets
compressed NDJSON streams
```

Admission future au cas par cas.

---

# 140. Future quality features différées

```text
semantic type inference
schema drift detection
anomaly thresholds
cross-run quality trends
reference-data lookups
data contracts registry
custom rule plugin DSL
```

Certaines pourront appartenir à V0.4 ou post-V1, mais ne doivent pas parasiter V0.3.

---

# 141. Relation avec V0.4

La V0.3 prépare directement V0.4 :

```text
Dataset
   ↓
Profile
   ↓
Validated Dataset
   ↓
────────────── V0.4 ──────────────
   ↓
Diff / Replay / Versioning
```

Un `DatasetProfile` stable permettra plus tard de comparer rapidement deux versions avant de calculer des diffs détaillés.

---

# 142. Ce qui appartient à V0.4

Ne pas implémenter en V0.3 :

```text
previous dataset lookup
version catalog
dataset snapshot identity
row-level diff
schema diff
replay command
publication based on diff
```

---

# 143. Risque — scope creep Data Quality

Risque : transformer `DatasetContract` en framework complet de règles.

Mitigation : seules les contraintes génériques et simples entrent en V0.3.

Règle :

> Si une règle nécessite un vocabulaire métier ou une ressource métier externe, elle n'appartient pas au core.

---

# 144. Risque — Dataset devient un mini dataframe

Mitigation :

```text
pas de filter/select/groupby/join/sort API dans Dataset
```

Ces opérations restent dans les jobs ou adapters.

---

# 145. Risque — profiling trop coûteux

Mitigation :

- métriques de base seulement ;
- coûts documentés ;
- pas de calculs statistiques sophistiqués ;
- architecture extensible.

---

# 146. Risque — Excel complexité infinie

Mitigation : cible stricte :

```text
.xlsx tabulaire simple
```

Pas de moteur Excel généraliste.

---

# 147. Risque — PyArrow devient le Dataset

Mitigation : `ParquetParser` est un adapter interne, et les tests de contrat vérifient que l'API core ne dépend pas d'Arrow.

---

# 148. Risque — optional dependencies cassent l'import

Mitigation : tests d'installation :

```text
pip install pyingestkit
python -c "import pyingestkit"
```

sans extras.

---

# 149. Risque — report fuite de données

Mitigation :

- pas de dump de lignes ;
- samples désactivés ou limités ;
- value previews tronqués/redacted ;
- tests secrets.

---

# 150. Risque — duplication Manifest / Metadata / Report

Mitigation : chaque support a une responsabilité :

```text
Manifest       = snapshot portable du run
MetadataStore  = index historique requêtable
Report         = diagnostic qualité détaillé
```

---

# 151. Definition of Done — Contracts V2

```text
[ ] allowed_values
[ ] pattern
[ ] min/max
[ ] min/max length
[ ] composite unique
[ ] logical key
[ ] stable issue codes
[ ] issue cap
[ ] no mutation
[ ] no coercion
[ ] deterministic ordering
[ ] unit tests
[ ] contract tests
```

---

# 152. Definition of Done — Profiling

```text
[ ] DatasetProfile
[ ] FieldProfile
[ ] row/field counts
[ ] null counts
[ ] distinct counts
[ ] observed types
[ ] length stats
[ ] safe min/max
[ ] duplicate rows
[ ] deterministic output
[ ] mixed types safe
```

---

# 153. Definition of Done — Reports

```text
[ ] validation.json
[ ] profile.json
[ ] schema version
[ ] JSON-safe values
[ ] manifest references
[ ] event emitted
[ ] no secret leakage
[ ] no RAW dumps
```

---

# 154. Definition of Done — NDJSON

```text
[ ] parser
[ ] line numbers
[ ] blank-line policy
[ ] object-only records
[ ] encoding errors
[ ] offline tests
[ ] Dataset linkage
```

---

# 155. Definition of Done — Excel

```text
[ ] optional openpyxl
[ ] xlsx
[ ] sheet selection
[ ] header row
[ ] duplicate header rejection
[ ] cell types
[ ] formula behavior
[ ] no macro execution
[ ] missing-extra message
[ ] offline tests
```

---

# 156. Definition of Done — Parquet

```text
[ ] optional pyarrow
[ ] parse simple parquet
[ ] column projection
[ ] null/timestamp/decimal
[ ] nested behavior documented
[ ] missing-extra message
[ ] core import without pyarrow
[ ] offline tests
```

---

# 157. Definition of Done — Non-régression V0.2

```text
[ ] demo.local_file
[ ] demo.http_csv
[ ] demo.http_json
[ ] HTTP retry tests offline
[ ] HTTP provenance tests
[ ] CSV parser tests
[ ] JSON parser tests
[ ] Dataset API
[ ] MetadataStore compatibility
```

---

# 158. Definition of Done — Quality gate

```text
[ ] unittest green
[ ] pytest green
[ ] Ruff lint green
[ ] Ruff format green
[ ] Mypy strict green
[ ] Bandit green
[ ] pip-audit green
[ ] compileall green
[ ] public API contract green
```

---

# 159. Definition of Done — Distribution gate

```text
[ ] framework wheel
[ ] framework sdist
[ ] demo wheel
[ ] demo sdist
[ ] fresh venv base wheel smoke
[ ] Excel extra smoke
[ ] Parquet extra smoke
[ ] all reference jobs run
```

---

# 160. Definition of Done — Release V0.3.0

```text
[ ] all milestones merged
[ ] RC1 vertical slices green
[ ] source ZIP clean
[ ] SHA256SUMS generated
[ ] validation evidence generated
[ ] tag v0.3.0
[ ] GitHub Release
[ ] artifacts attached
[ ] V0.3 administratively closed
```

---

# 161. Séquence d'implémentation détaillée

```text
LOT 0   Branch + baseline V0.2.0
LOT 1   Contract models V2
LOT 2   Constraint evaluation
LOT 3   Composite keys / uniqueness
LOT 4   ValidationIssue V2
LOT 5   DatasetProfiler models
LOT 6   DatasetProfiler engine
LOT 7   Quality report writer
LOT 8   Manifest/events integration
LOT 9   NDJSON parser
LOT 10  Excel optional adapter
LOT 11  Parquet optional adapter
LOT 12  Demo jobs
LOT 13  CLI/status integration
LOT 14  Docs/ADRs
LOT 15  Hardening
LOT 16  Wheel/extras smoke tests
LOT 17  RC1
LOT 18  Stable release
```

---

# 162. Lot 0 — Baseline

Actions :

```bash
git checkout main
git pull
git checkout -b feat/v0.3-quality-formats
```

Vérifier avant toute modification :

```bash
make release-check
```

La baseline doit être `v0.2.0` clean.

---

# 163. Lot 1 — Contract models V2

Modifier avec compatibilité :

```text
src/pyingestkit/contracts/dataset.py
```

Éventuellement extraire :

```text
constraints.py
```

mais seulement si la lisibilité le justifie.

---

# 164. Lot 2 — Constraint evaluation

Ordre de validation recommandé par champ :

```text
presence
nullability
type
allowed_values
pattern
range
length
uniqueness
```

Cela permet d'éviter des erreurs dérivées absurdes lorsque le type est déjà invalide.

---

# 165. Lot 3 — Composite keys

Implémenter une canonicalisation sûre des tuples de clé.

Les valeurs non hashables doivent être gérées explicitement ou rejetées avec issue contractuel.

---

# 166. Lot 4 — Issue model

Garantir backward compatibility du constructeur V0.2 si possible.

Éviter de casser les utilisateurs pour ajouter des métadonnées facultatives.

---

# 167. Lot 5 — Profiling models

Créer :

```text
profiling/models.py
```

avec dataclasses `slots=True`, frozen si possible.

---

# 168. Lot 6 — Profiling engine

Implémenter les métriques de base avec une seule passe autant que raisonnable.

La lisibilité prime sur une micro-optimisation prématurée.

---

# 169. Lot 7 — Report writer

Écrire sous :

```text
reports/validation.json
reports/profile.json
```

via `ArtifactStore`.

---

# 170. Lot 8 — Runtime integration

Le Runner ne doit pas devenir conscient de tous les types métier possibles.

Deux stratégies possibles :

1. steps explicitement écrivent les reports ;
2. runtime reconnaît des outputs framework-owned comme `DatasetProfile` et `QualityReport` comme il reconnaît déjà `ValidationResult`.

Préférence : intégration limitée aux outputs framework-owned, avec tests et sans sérialiser tout output arbitraire.

---

# 171. Lot 9 — NDJSON

Implémentation stdlib, pas de dépendance.

---

# 172. Lot 10 — Excel

Ajouter extra, parser, fixtures et tests.

Ne pas modifier les deps runtime de base.

---

# 173. Lot 11 — Parquet

Ajouter extra, parser, fixtures et tests.

Valider disponibilité PyArrow avant de figer les bornes.

---

# 174. Lot 12 — Demo jobs

Ajouter progressivement les entry points et mettre à jour les tests d'isolation/plugin discovery.

---

# 175. Lot 13 — CLI

Enrichir `status`, pas de prolifération de commandes.

---

# 176. Lot 14 — Documentation

ADRs + guides + architecture note.

Chaque milestone doit être documenté avant ZIP.

---

# 177. Lot 15 — Hardening

Vérifier :

```text
secret leakage
resource errors
mixed data types
empty datasets
invalid files
missing optional dependencies
format edge cases
```

---

# 178. Lot 16 — Distribution

Le wheel smoke doit prouver :

```text
base install
excel install
parquet install
demo install
```

---

# 179. Lot 17 — RC1

Construire les vertical slices complets et tous les reports.

Pas de nouvelle fonctionnalité après RC1 sauf correction de bug bloquante.

---

# 180. Lot 18 — Stable

Bump `0.3.0`, build, checksums, tag, release.

---

# 181. Critères de réussite produit

La V0.3 est réussie si un job pack peut faire ceci sans plomberie maison :

```text
acquire RAW
parse NDJSON/Excel/Parquet
obtain Dataset
validate generic structure/value constraints
profile dataset
write quality evidence
persist run metadata
inspect status
```

---

# 182. Critère ultime

Un développeur doit pouvoir écrire un job multi-format et répondre immédiatement :

```text
Qu'ai-je reçu ?
Sous quelle forme ?
Combien de lignes/champs ?
Quels types ai-je réellement observés ?
Le dataset respecte-t-il mon contrat ?
Où sont les anomalies ?
Où est la preuve de qualité du run ?
```

sans dépendre d'un notebook Pandas ad hoc.

---

# 183. Architecture signature V0.3

```text
                         EXTERNAL DATA
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Acquisition V0.2      │
                  │ Local / HTTP / Retry  │
                  └───────────┬───────────┘
                              ▼
                         RawArtifact
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Text formats       Workbook        Columnar
       CSV/JSON/NDJSON       XLSX            Parquet
             └────────────────┼────────────────┘
                              ▼
                           Dataset
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       DatasetContract V2             DatasetProfiler
               │                             │
               ▼                             ▼
       ValidationResult               DatasetProfile
               └──────────────┬──────────────┘
                              ▼
                       Quality Evidence
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
              reports      Manifest     Events/Metadata
```

---

# 184. Roadmap après V0.3

```text
V0.1  FOUNDATION
      ✅ frozen

V0.2  ACQUISITION
      ✅ released

V0.3  QUALITY & FORMATS
      ← current planned milestone

V0.4  DIFF / REPLAY / VERSIONING

V0.5  PERSISTENCE TARGETS

V0.6  OBJECT STORAGE

V1.0  STABLE FRAMEWORK CONTRACT
```

---

# 185. Décision de lancement

La V0.3 peut démarrer lorsque :

```text
V0.2.0 release-check ✅
V0.2.0 tag ✅
V0.2.0 GitHub Release ✅
V0.2.0 artifacts/checksums ✅
V0.2.0 administratively closed ✅
```

Ces conditions sont désormais satisfaites.

Le premier jalon d'exécution est donc :

```text
V0.3.0-a1 — Quality Contracts V2
```

et le premier ZIP :

```text
pyingestkit-v0.3.0-a1-quality-contracts.zip
```

---

# 186. Conclusion

V0.2.0 a donné à PyIngestKit une acquisition industrialisable et un premier contrat de données structuré.

V0.3.0 doit maintenant rendre ce dataset **mesurable, qualifiable, auditable et multi-format**, tout en résistant à trois tentations :

```text
1. devenir un dataframe framework ;
2. devenir une plateforme Data Quality ;
3. absorber les normalisations métier.
```

La trajectoire retenue est volontairement progressive :

```text
Contracts V2
   ↓
Profiling + Reports
   ↓
NDJSON + Excel
   ↓
Parquet
   ↓
Full E2E RC
   ↓
V0.3.0 Quality & Formats Release
```

La V0.3 constitue ainsi le pont naturel entre :

```text
V0.2 — obtenir un Dataset fiable
```

et :

```text
V0.4 — comprendre ce qui a changé entre deux versions de Dataset
```

sans compromettre la doctrine d'origine de PyIngestKit : fournir la plomberie générique de l'ingestion, pas remplacer l'écosystème data.

---

## Document status

```text
Baseline             : PyIngestKit v0.2.0
Milestone            : V0.3.0 Quality & Formats
Architecture         : PROPOSED / READY FOR IMPLEMENTATION
First implementation : V0.3.0-a1 Quality Contracts V2
First ZIP            : pyingestkit-v0.3.0-a1-quality-contracts.zip
Next major milestone : V0.4 Diff / Replay / Versioning
```
