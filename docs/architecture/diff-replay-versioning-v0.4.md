# PyIngestKit V0.4 — Diff / Replay / Versioning Architecture & Implementation Plan

**Document:** `03_PYINGESTKIT_V0.4_DIFF_REPLAY_VERSIONING_ARCHITECTURE_IMPLEMENTATION_PLAN.md`  
**Target release:** `v0.4.0`  
**Milestone name:** **DIFF / REPLAY / VERSIONING**  
**Baseline:** `v0.3.0 — Quality & Formats Release`  
**Status:** Architecture & implementation plan — ready for execution after administrative closure of V0.3.0  
**Date:** 2026-09-04

---

# 0. Résumé exécutif

PyIngestKit V0.3.0 a étendu la chaîne d'ingestion en ajoutant des **Quality Contracts V2**, du **Dataset Profiling**, des **Quality Reports** et de nouveaux formats structurés — NDJSON, Excel et Parquet — tout en préservant le `Dataset` engine-neutral et matérialisé.

La V0.4 ne doit ni ajouter de nouveaux formats, ni ouvrir le chantier des targets SQL/warehouse de la V0.5. Elle doit résoudre une autre famille de problèmes, directement liée à la fiabilité opérationnelle d'un système d'ingestion :

> **Comment savoir ce qui a changé entre deux versions d'un dataset, conserver une identité stable de chaque version, maintenir une version publiée canonique, et rejouer un run depuis son RAW sans réinterroger la source ?**

La V0.4 ajoute donc trois capacités transverses :

1. **Diff** — comparer un dataset candidat à une version de référence de manière déterministe, key-aware et configurable ;
2. **Versioning** — calculer une identité de contenu, sérialiser un snapshot round-trip, historiser les versions et représenter la version publiée courante ;
3. **Replay** — créer un nouveau run à partir d'un RAW précédemment capturé, sans nouvelle acquisition réseau/fichier, avec une lineage explicite et une vérification de reproductibilité lorsque possible.

La signature architecturale cible devient :

```text
External Source
      │
      ▼
Acquisition
      │
      ▼
RawArtifact ───────────────────────────────────────────┐
      │                                                │
      ▼                                                │
Parser                                                │
      │                                                │
      ▼                                                │
Dataset                                               │
      │                                                │
      ├────────► Quality / Validation / Profiling      │
      │                                                │
      ├────────► DatasetFingerprinter                  │
      │                    │                           │
      │                    ▼                           │
      │              DatasetFingerprint               │
      │                    │                           │
      │                    ▼                           │
      │              DatasetSnapshot                  │
      │                    │                           │
      │                    ▼                           │
      │             DatasetVersionStore               │
      │                                                │
      ├────────► DatasetDiffer ◄──── PublishedDataset │
      │                    │                           │
      │                    ▼                           │
      │                DatasetDiff                    │
      │                    │                           │
      │                    ▼                           │
      │               diff.json                       │
      │                                                │
      └────────► publish/promote version               │
                           │                           │
                           ▼                           │
                    PublishedDataset                  │
                                                       │
                                                       ▼
                                               pyingest replay
                                                       │
                                                       ▼
                                             Replay RAW Resolver
                                                       │
                                                       └──► new Run
```

La doctrine centrale reste :

```text
Diff              ≠ Transformation
Versioning        ≠ Git pour les données
Replay            ≠ Scheduler retry
PublishedDataset  ≠ dernier fichier écrit
DatasetVersion    ≠ version SemVer du package
Snapshot          ≠ pickle
Replay            ≠ nouvel appel HTTP
PyIngestKit       ≠ orchestrateur
```

La V0.4 sera découpée en six jalons :

```text
V0.4.0-a1  DATASET FINGERPRINTS + DIFF ENGINE
V0.4.0-a2  DIFF REPORTS + RUNTIME / METADATA OBSERVATION
V0.4.0-b1  DATASET SNAPSHOTS + VERSION REGISTRY + PUBLISHED DATASET
V0.4.0-b2  REPLAY FROM RAW + LINEAGE
V0.4.0-rc1 DIFF / REPLAY / VERSIONING E2E
V0.4.0     DIFF / REPLAY / VERSIONING RELEASE
```

Proposition d'artefacts de livraison :

```text
pyingestkit-v0.4.0-a1-diff-engine.zip
pyingestkit-v0.4.0-a2-diff-reports-runtime.zip
pyingestkit-v0.4.0-b1-versioning-published.zip
pyingestkit-v0.4.0-b2-replay-lineage.zip
pyingestkit-v0.4.0-rc1-diff-replay-versioning-e2e.zip
pyingestkit-v0.4.0.zip
```

---

# 1. Précondition de lancement

La conception V0.4 peut être préparée pendant la qualification finale de V0.3.0, mais l'implémentation ne doit commencer qu'une fois la release V0.3.0 administrativement close :

```text
V0.3.0 code stable                  ✅ attendu
V0.3.0 make release-check           ✅ requis
V0.3.0 CI/Security                  ✅ requis
V0.3.0 merge sur main               ✅ requis
V0.3.0 tag                          ✅ requis
V0.3.0 GitHub Release               ✅ requis
V0.3.0 checksums                    ✅ vérifiés
```

La règle est importante :

> **V0.4 ne doit pas devenir le lieu où l'on termine V0.3.**

Toute correction V0.3 découverte pendant cette fermeture reste une correction de stabilisation V0.3.

---

# 2. Baseline officielle héritée

## 2.1. Foundation V0.1.6

La V0.4 réutilise sans les réinventer :

- `Job`, `Step`, `Pipeline`, `Runner` ;
- `RunContext` ;
- API déclarative `@job` / `@step` ;
- `ArtifactStore` ;
- `AtomicPublisher` ;
- `MetadataStore` ;
- SQLite / PostgreSQL metadata adapters ;
- events runtime ;
- manifest ;
- CLI Typer/Rich ;
- plugin entry points ;
- logging et redaction ;
- security / quality / wheel-smoke release gates.

## 2.2. Acquisition V0.2.0

La V0.4 dépend directement de :

```text
Source
  ↓
RawArtifact
  ↓
sha256
  ↓
provenance
```

Le replay n'est possible que parce que le RAW est déjà capturé de manière immuable et identifiable.

## 2.3. Quality & Formats V0.3.0

La V0.4 hérite de :

```text
Dataset
DatasetContract V2
ValidationResult
DatasetProfiler
DatasetProfile
Quality Reports
CSV / JSON / NDJSON / XLSX / Parquet
```

Le diff et le versioning s'opèrent **sur le Dataset canonique du framework**, pas directement sur Pandas, Polars, Arrow ou le format source.

---

# 3. Mission de la V0.4

La V0.4 doit répondre à quatre questions opérationnelles :

```text
1. Ce dataset est-il réellement différent du précédent ?

2. Qu'est-ce qui a été ajouté, supprimé ou modifié ?

3. Quelle version est actuellement la référence publiée ?

4. Puis-je reproduire ce run depuis son RAW sans recontacter la source ?
```

Elle transforme la chaîne :

```text
RAW → PARSE → VALIDATE → REPORT
```

vers :

```text
RAW → PARSE → VALIDATE → FINGERPRINT → DIFF → VERSION → PUBLISH
  ▲                                                        │
  └──────────────────── REPLAY ─────────────────────────────┘
```

---

# 4. Objectifs fonctionnels

La V0.4 doit fournir :

- un fingerprint déterministe d'un `Dataset` ;
- un moteur de diff générique ;
- un diff basé sur clé logique ;
- un mode keyless limité à added/removed ;
- un diff de schéma ;
- des champs ignorés ou explicitement comparés ;
- des résultats bornés et déterministes ;
- un rapport `diff.json` ;
- une sérialisation snapshot round-trip ;
- un registre de versions de dataset ;
- une notion `PublishedDataset` ;
- une publication atomique de la référence courante ;
- un replay depuis un RAW antérieur ;
- une lineage replay explicite ;
- une vérification de reproductibilité par fingerprint ;
- des commandes CLI d'inspection ;
- un E2E offline démontrant version 1 → version 2 → diff → publish → replay.

---

# 5. Non-objectifs

La V0.4 n'introduira pas :

```text
PostgresTarget
SnowflakeTarget
S3Target
MinioArtifactStore
bulk load warehouse
CDC
Kafka
streaming Dataset
branching de datasets façon Git
merge 3-way
résolution de conflits
schema registry distant
catalogue de données
retention/garbage collection automatique
scheduler
Celery
async Runner
data lake transaction log
Delta Lake / Iceberg / Hudi
```

Ces sujets appartiennent soit à V0.5+, soit à des systèmes externes.

---

# 6. Les quatre identités à ne pas confondre

La V0.4 introduit plusieurs formes de version. Il faut les nommer clairement.

```text
PyIngestKit package version
  ex: 0.4.0

Job version
  ex: public.postal_codes 1.7.0

RawArtifact sha256
  identité des bytes acquis

Dataset fingerprint / Dataset version id
  identité logique du Dataset parsé/normalisé
```

Aucune de ces identités ne doit être utilisée à la place d'une autre.

---

# 7. Dataset fingerprint

Le fingerprint est l'empreinte déterministe du contenu logique d'un Dataset.

Proposition :

```python
fingerprint = DatasetFingerprinter().fingerprint(dataset)
```

Résultat :

```text
sha256-<64 hex chars>
```

Exemple :

```text
sha256-7f81b0d6a18b...
```

Cette valeur peut devenir l'identité d'une version de dataset.

---

# 8. Fingerprint ≠ Raw SHA-256

Deux RAW différents peuvent produire le même Dataset logique :

```text
CSV avec ordre différent
        ↓
normalisation stable
        ↓
Dataset identique
```

Inversement :

```text
RAW identique
+
job version différente
        ↓
Dataset potentiellement différent
```

Il faut donc conserver les deux empreintes.

---

# 9. Canonicalisation commune

Le diff, le fingerprint et le snapshot ont besoin d'une notion cohérente de valeur canonique.

V0.4 doit créer une primitive interne commune, par exemple :

```text
CanonicalValueCodec
```

ou :

```text
canonicalize_value()
```

Elle ne doit pas être exposée comme une API métier.

Objectifs :

- type-aware ;
- déterministe ;
- JSON-safe ;
- round-trip quand utilisée par le snapshot codec ;
- stable entre processus ;
- sans `repr()` arbitraire.

---

# 10. Types canoniques minimaux

Le codec doit couvrir les valeurs susceptibles d'être produites par V0.3 :

```text
None
bool
int
float
str
bytes
decimal.Decimal
date
datetime
list
tuple
dict / Mapping
```

Les types non supportés doivent provoquer une erreur explicite.

Ne jamais fallback vers :

```python
repr(value)
```

pour une preuve persistée.

---

# 11. Comparaison type-aware

Python considère :

```python
True == 1
1 == 1.0
```

Pour un diff de données, cette égalité peut masquer un changement de type réel.

La V0.4 doit donc comparer les valeurs canoniques avec leur type.

Par défaut :

```text
True  ≠ 1
1     ≠ 1.0
```

Aucune coercion implicite.

---

# 12. Valeurs flottantes spéciales

Le codec doit traiter explicitement :

```text
NaN
+Infinity
-Infinity
-0.0
```

Il faut éviter de dépendre de l'égalité IEEE standard de `NaN`.

Une sérialisation tagged et déterministe est préférable.

---

# 13. Datetime

Les `datetime` doivent conserver :

- la valeur ISO-8601 ;
- l'offset/timezone lorsqu'il existe ;
- la distinction date/datetime.

Le codec ne doit pas convertir silencieusement un datetime timezone-aware vers un datetime naïf.

---

# 14. Decimal

`decimal.Decimal` doit être encodé en chaîne décimale exacte.

Interdit :

```text
Decimal → float
```

car cela peut perdre de la précision et modifier le fingerprint.

---

# 15. Bytes

Les bytes doivent être encodés explicitement, par exemple :

```json
{
  "$type": "bytes",
  "encoding": "base64",
  "value": "..."
}
```

Aucun dump binaire brut dans du JSON.

---

# 16. Mapping imbriqué

Un mapping imbriqué doit être canonisé de manière indépendante de son ordre d'insertion.

Exemple :

```python
{"a": 1, "b": 2}
```

et :

```python
{"b": 2, "a": 1}
```

sont identiques logiquement.

---

# 17. Ordre des lignes

Le fingerprint doit avoir une politique explicite d'ordre.

Recommandation V0.4 :

```python
DatasetFingerprintPolicy(
    order_sensitive=False,
)
```

par défaut.

Raison : une source de référentiel qui réordonne ses lignes sans changer les données ne doit pas nécessairement créer une nouvelle version.

Un mode explicite :

```python
order_sensitive=True
```

doit rester possible pour des datasets où la séquence elle-même porte du sens.

---

# 18. Fingerprint et champs

Le fingerprint doit inclure :

- le schéma/ordre des champs du Dataset ;
- les valeurs canoniques ;
- les doublons ;
- la politique d'ordre choisie.

Il ne doit pas inclure :

```text
run_id
retrieved_at
source URL
path local
durée du run
```

Ces données appartiennent à la provenance, pas à l'identité du Dataset.

---

# 19. API de fingerprint proposée

```python
from pyingestkit.versioning import DatasetFingerprinter, DatasetFingerprintPolicy

fingerprinter = DatasetFingerprinter(
    DatasetFingerprintPolicy(order_sensitive=False)
)

fingerprint = fingerprinter.fingerprint(dataset)
```

Résultat immuable :

```python
DatasetFingerprint(
    algorithm="sha256",
    value="...",
    order_sensitive=False,
    row_count=35892,
    field_count=12,
)
```

Le wrapper typé est préférable à une string opaque lorsqu'il reste léger.

---

# 20. Moteur de diff

API cible :

```python
from pyingestkit.diff import DatasetDiffer, DiffPolicy

policy = DiffPolicy(
    key_fields=("id",),
    ignore_fields=("updated_at",),
)

result = DatasetDiffer(policy).compare(previous, candidate)
```

---

# 21. Modèle mental du diff

```text
previous Dataset
       │
       ├──────────────┐
       │              │
       ▼              ▼
key extraction    value canonicalization
       │              │
       └──────┬───────┘
              ▼
         DatasetDiffer
              ▲
              │
candidate Dataset
              │
              ▼
          DatasetDiff
```

---

# 22. DiffPolicy

Proposition :

```python
DiffPolicy(
    key_fields=("id",),
    ignore_fields=(),
    compare_fields=None,
    order_sensitive=False,
    max_entries=1_000,
    capture_values=False,
)
```

`ignore_fields` et `compare_fields` doivent être mutuellement exclusifs.

---

# 23. Keyed diff

Le mode recommandé est key-aware.

Exemple :

```text
key_fields = ("country_code", "postal_code")
```

Le moteur peut alors distinguer :

```text
ADDED
REMOVED
CHANGED
UNCHANGED
```

---

# 24. Clés dupliquées

Un diff keyed ne peut pas être fiable si une clé est dupliquée.

Par défaut :

```text
duplicate key in previous  → DiffError
duplicate key in candidate → DiffError
```

Le moteur ne doit pas choisir arbitrairement "la première ligne".

---

# 25. Null dans une clé

Par défaut, une clé de diff contenant `None` ou un champ manquant est invalide.

Cela doit être un `DiffError` de configuration/données et non une simple modification.

La logique est cohérente avec la notion de `primary_key` V0.3.

---

# 26. Keyless diff

Le framework doit permettre un mode sans clé pour des datasets simples.

Dans ce mode :

```text
row exact in candidate only → ADDED
row exact in previous only  → REMOVED
```

Il n'existe pas de notion fiable de `CHANGED` sans identité de ligne.

Donc :

```text
keyless diff
  → added / removed only
  → changed = 0
```

---

# 27. Multiset, pas seulement set

Les doublons de lignes doivent être respectés.

Exemple :

```text
previous:
A
A

candidate:
A
```

résultat :

```text
removed = 1
```

Le keyless diff doit donc travailler comme un multiset canonique.

---

# 28. Diff de schéma

`DatasetDiff` doit contenir une composante de schéma :

```text
added_fields
removed_fields
common_fields
field_order_changed
```

Le diff de schéma ne doit pas être confondu avec le diff des lignes.

---

# 29. Changement de champ

En mode keyed, une ligne est `CHANGED` lorsqu'au moins un champ comparé change.

Le résultat doit fournir :

```text
key
changed_fields
```

et éventuellement des valeurs avant/après si explicitement activées.

---

# 30. Champs ignorés

Exemple :

```python
DiffPolicy(
    key_fields=("id",),
    ignore_fields=("retrieved_at", "last_seen_at"),
)
```

Un changement uniquement sur ces champs ne produit pas un `CHANGED`.

---

# 31. Champs significatifs

Alternative whitelist :

```python
DiffPolicy(
    key_fields=("id",),
    compare_fields=("name", "status", "category"),
)
```

Le reste n'est pas pris en compte dans le changement métier.

---

# 32. `ignore_fields` vs `compare_fields`

Ces deux modes sont mutuellement exclusifs pour éviter les politiques ambiguës.

Le constructeur doit refuser :

```python
DiffPolicy(
    ignore_fields=("a",),
    compare_fields=("b",),
)
```

---

# 33. Champs de clé et champs ignorés

Un champ de clé ne peut pas être ignoré.

Refuser :

```text
key_fields ∩ ignore_fields != ∅
```

Les `compare_fields` peuvent ne pas contenir les clés car la clé sert à l'identité, pas à la comparaison de contenu.

---

# 34. Missing vs None

Le Dataset V0.3 sait distinguer un champ absent d'un champ présent avec `None`.

Le diff doit conserver cette sémantique :

```text
missing ≠ None
```

par défaut.

Cela permet de détecter des changements de structure dans des JSON/NDJSON sparsés.

---

# 35. Valeurs avant/après

Les diff reports peuvent contenir des données sensibles.

Le comportement par défaut doit être :

```text
capture_values=False
```

Ainsi une entrée `CHANGED` contient :

```text
key
changed_fields
```

mais pas les records complets.

---

# 36. `capture_values=True`

Un utilisateur peut explicitement demander les valeurs :

```python
DiffPolicy(capture_values=True)
```

Même dans ce cas :

- les rapports doivent appliquer les règles de preview/redaction ;
- les logs ne doivent jamais dumper les lignes complètes ;
- les snapshots restent le lieu de vérité complet, pas les logs.

---

# 37. DiffResult / DatasetDiff

Proposition :

```python
@dataclass(frozen=True, slots=True)
class DatasetDiff:
    previous_fingerprint: DatasetFingerprint
    candidate_fingerprint: DatasetFingerprint
    added_count: int
    removed_count: int
    changed_count: int
    unchanged_count: int
    schema: SchemaDiff
    entries: tuple[DiffEntry, ...]
    entries_truncated: bool
```

---

# 38. DiffEntry

Proposition :

```python
@dataclass(frozen=True, slots=True)
class DiffEntry:
    kind: DiffKind
    key: tuple[object, ...] | None
    changed_fields: tuple[str, ...] = ()
    before: Mapping[str, object] | None = None
    after: Mapping[str, object] | None = None
```

`before` / `after` restent `None` par défaut.

---

# 39. DiffKind

Enum stable :

```text
ADDED
REMOVED
CHANGED
```

`UNCHANGED` n'a pas besoin d'une entrée détaillée ; son compteur suffit.

---

# 40. Ordre déterministe des entrées

Les entrées doivent être produites dans un ordre stable.

Recommandation keyed :

```text
ADDED   triées par clé canonique
REMOVED triées par clé canonique
CHANGED triées par clé canonique
```

Cela facilite :

- tests ;
- rapports reproductibles ;
- revue humaine ;
- hashing éventuel des rapports.

---

# 41. Limite d'entrées

Comme les issues V0.3, un diff peut être énorme.

`DiffPolicy.max_entries` limite le détail :

```text
counts exacts
entries bornées
entries_truncated explicite
```

Contrairement à `ValidationResult.max_issues`, il est raisonnable de maintenir les comptes exacts car le moteur parcourt de toute façon les deux datasets pour comparer les index.

---

# 42. Complexité visée

Keyed diff :

```text
O(n + m) mémoire / temps moyen
```

hors tri final des entrées détaillées.

Keyless multiset :

```text
O(n + m)
```

avec canonicalisation des lignes.

Éviter absolument un algorithme :

```text
O(n × m)
```

---

# 43. Diff et Dataset matérialisé

V0.4 reste alignée sur la boundary V0.3 :

```text
Dataset = matérialisé en mémoire
```

Le diff peut donc créer des index mémoire exacts.

Les très grands datasets restent un futur chantier distinct.

---

# 44. Diff ≠ fuzzy matching

V0.4 n'essaie pas de déduire que :

```text
"Société A" → "Societe A"
```

est "presque identique".

Pas de :

- Levenshtein ;
- matching probabiliste ;
- entity resolution ;
- fuzzy joins.

Le diff compare des valeurs normalisées par le job.

---

# 45. Diff ≠ transformation

Le moteur ne modifie jamais les Datasets.

```python
before_previous = previous.to_rows()
before_candidate = candidate.to_rows()

result = differ.compare(previous, candidate)

assert previous.to_rows() == before_previous
assert candidate.to_rows() == before_candidate
```

---

# 46. Diff report

Le format machine-readable canonique sera :

```text
reports/diff.json
```

ou, en cas de plusieurs diffs dans un run :

```text
reports/<step>/diff.json
```

La convention finale doit éviter tout overwrite silencieux.

---

# 47. Schéma `diff.json`

Proposition :

```json
{
  "report_version": "1",
  "kind": "diff",
  "dataset_id": "public.postal_codes",
  "previous_version_id": "sha256-...",
  "candidate_fingerprint": "sha256-...",
  "policy": {
    "key_fields": ["postal_code", "commune"],
    "ignore_fields": ["updated_at"]
  },
  "summary": {
    "added": 12,
    "removed": 2,
    "changed": 31,
    "unchanged": 6350
  },
  "schema": {
    "added_fields": [],
    "removed_fields": [],
    "field_order_changed": false
  },
  "entries_truncated": false,
  "entries": []
}
```

---

# 48. `report_version`

Comme les rapports V0.3 :

```text
report_version = "1"
```

Cette version est indépendante de `pyingestkit.__version__`.

---

# 49. Manifest integration

Le manifest V0.3 possède déjà :

```text
reports[]
```

Le diff s'intègre additivement :

```json
{
  "kind": "diff",
  "path": "reports/diff.json",
  "step": "CompareCandidate"
}
```

Pas besoin d'embarquer tout le diff dans le manifest.

---

# 50. Events de diff

Événements proposés :

```text
DIFF_STARTED
DIFF_COMPLETED
DIFF_REPORT_WRITTEN
```

Payloads compacts :

```text
added_count
removed_count
changed_count
previous_version_id
candidate_fingerprint
report_path
```

Pas de records complets dans les events.

---

# 51. Runtime observation

`Runner` peut observer un `DatasetDiff` dans un `StepResult.output`, comme il observe déjà `ValidationResult` et `DatasetProfile`.

Le principe doit rester générique :

```text
Step output
   ↓
DatasetDiff discovered
   ↓
write diff report
   ↓
manifest ref
   ↓
events
```

Le Runner ne doit pas calculer automatiquement un diff pour chaque Dataset.

---

# 52. Pourquoi le diff n'est pas automatique

Un diff nécessite des choix métier/génériques explicites :

```text
quelle clé ?
quelle baseline ?
quels champs ignorer ?
quels champs comparer ?
```

Le framework ne peut pas les deviner correctement.

Donc :

```text
profiling explicite
validation explicite
diff explicite
```

---

# 53. Diff metadata

La V0.4 peut ajouter une metadata queryable légère pour les diffs.

Table additive proposée :

```text
dataset_diffs
```

Champs :

```text
id
run_id
step_name
dataset_id
previous_version_id
candidate_fingerprint
added_count
removed_count
changed_count
unchanged_count
entries_truncated
report_path
created_at
```

---

# 54. Ne pas casser `MetadataStore`

Le `MetadataStore` V0.3 est un ABC public.

Ajouter de nouvelles méthodes abstraites directement briserait les adaptateurs tiers.

Recommandation : introduire des capability interfaces optionnelles :

```text
DiffMetadataCapability
VersionMetadataCapability
ReplayMetadataCapability
```

Les stores officiels SQLite/PostgreSQL les implémentent.

Un store custom V0.3 qui n'implémente pas ces capabilities continue de fonctionner, avec artefacts/events mais moins de requêtabilité V0.4.

---

# 55. Schéma SQL additif

V0.4 ne doit pas modifier les colonnes des tables V0.3 pour les fonctions nouvelles.

Préférer de nouvelles tables :

```text
dataset_diffs
dataset_versions
dataset_version_runs
published_datasets
replay_runs
run_reproducibility
```

`metadata.create_all()` peut les créer sur une base existante.

Cette stratégie reste compatible avec la posture pré-Alembic tant que les migrations restent purement additives.

---

# 56. Diff guards

Le moteur de diff doit permettre au job d'appliquer des garde-fous génériques avant publication.

Exemple :

```python
DiffGuard(
    max_removed_ratio=0.10,
    max_changed_ratio=0.50,
    allow_schema_changes=False,
)
```

Le guard analyse un `DatasetDiff` ; il ne recalcule pas le diff.

---

# 57. DiffGuardResult

Proposition :

```text
PASSED
FAILED
REVIEW
```

Il peut être représenté par la mécanique de validation existante ou un petit résultat dédié.

Recommandation : réutiliser `ValidationResult` lorsque les contraintes sont naturellement exprimables comme validations de publication, afin d'éviter une seconde hiérarchie de qualité.

---

# 58. Diff guard ≠ règle métier

Le framework peut proposer des seuils génériques :

```text
max removed count
max removed ratio
max changed count
max changed ratio
schema changes allowed?
```

Le job décide des valeurs.

Il ne doit pas embarquer :

```text
"pas plus de 10 codes postaux supprimés en France"
```

Cette règle appartient au pack métier.

---

# 59. Dataset Snapshot

Le versioning nécessite un snapshot round-trip du Dataset.

Un snapshot est :

> une représentation sérialisée, déterministe et restaurable du Dataset, indépendante du format source.

---

# 60. Pourquoi ne pas conserver uniquement le RAW

Le RAW permet le replay, mais pas un diff historique instantané sans réexécuter le parsing et la normalisation.

Le snapshot permet :

```text
load previous version
        ↓
Dataset
        ↓
DIFF
```

sans reparser l'ancien RAW.

---

# 61. Pourquoi JSON snapshot

La V0.4 doit privilégier un format de snapshot interne :

```text
JSON versionné + valeurs typées/tagged
```

Avantages :

- stdlib ;
- inspectable ;
- portable ;
- pas de dépendance dataframe ;
- pas d'exécution de code ;
- contrôlable par schema version.

---

# 62. Interdiction du pickle

Le snapshot ne doit jamais utiliser `pickle`.

Raisons :

```text
security
portability
version coupling
arbitrary code execution
Python implementation coupling
```

---

# 63. Snapshot schema

Proposition :

```json
{
  "snapshot_version": "1",
  "dataset": {
    "fields": ["id", "name"],
    "rows": [
      {
        "id": {"$type": "int", "value": "1"},
        "name": {"$type": "str", "value": "A"}
      }
    ]
  }
}
```

L'implémentation peut être plus compacte tant que la sémantique reste explicite et round-trip.

---

# 64. Snapshot metadata

Un fichier adjacent `version.json` doit porter la provenance de version :

```json
{
  "version_schema": "1",
  "dataset_id": "public.postal_codes",
  "version_id": "sha256-...",
  "fingerprint": "sha256-...",
  "created_from_run_id": "...",
  "job_id": "public.postal_codes",
  "job_version": "1.4.0",
  "source_artifact_id": "...",
  "source_raw_sha256": "...",
  "created_at": "..."
}
```

---

# 65. Snapshot de données sensibles

Contrairement aux quality reports, un snapshot doit conserver les vraies valeurs pour être round-trip.

Donc :

```text
snapshot = donnée potentiellement sensible
```

Conséquences :

- jamais dans les logs ;
- jamais dans les events ;
- ne pas le joindre automatiquement à une GitHub Release ;
- permissions filesystem à considérer ;
- chiffrement au repos délégué au disque/object store/OS ;
- politique de retention à documenter.

---

# 66. Pas de retention automatique en V0.4

V0.4 ne supprime automatiquement aucune version.

Pas encore de :

```text
prune
gc
TTL
max versions
```

Une stratégie de retention automatique doit attendre des cas réels et les futurs stores.

---

# 67. DatasetVersion

Modèle proposé :

```python
@dataclass(frozen=True, slots=True)
class DatasetVersion:
    dataset_id: str
    version_id: str
    fingerprint: DatasetFingerprint
    snapshot_path: str
    created_at: datetime
    created_from_run_id: str
    job_id: str
    job_version: str
    source_artifact_id: str | None
    source_raw_sha256: str | None
```

---

# 68. Version ID content-addressed

Recommandation :

```text
version_id = fingerprint
```

avec un format filesystem-safe :

```text
sha256-<hex>
```

Ainsi :

```text
same logical dataset content
→ same dataset version id
```

---

# 69. Même version, plusieurs runs

Plusieurs runs peuvent produire le même fingerprint.

Le registre ne doit pas dupliquer les bytes inutilement.

Il doit en revanche conserver la relation :

```text
version X produced by runs A, B, C
```

Table proposée :

```text
dataset_version_runs
```

---

# 70. `dataset_id`

`dataset_id` identifie la ressource logique versionnée.

Par défaut :

```text
dataset_id = job_id
```

Exemples :

```text
public.postal_codes
amifond.naf
client_x.products
```

Le job peut fournir un autre `dataset_id` lorsque plusieurs datasets publiés sortent du même job, mais cela doit rester explicite.

---

# 71. DatasetVersionStore

Abstraction proposée :

```python
class DatasetVersionStore(ABC):
    def create_version(...): ...
    def get_version(...): ...
    def list_versions(...): ...
    def get_published(...): ...
    def publish(...): ...
```

---

# 72. FilesystemDatasetVersionStore

V0.4 livre uniquement :

```text
FilesystemDatasetVersionStore
```

Les targets de données SQL appartiennent à V0.5.

Le version store n'est pas un `PostgresTarget` déguisé.

---

# 73. Workspace V0.4

Extension proposée :

```text
.pyingest/
├── state/
│   └── pyingest.sqlite3
├── logs/
│   └── pyingest.log
├── runs/
│   └── ...
├── versions/
│   └── <namespace>/<job>/
│       └── sha256-<fingerprint>/
│           ├── dataset.snapshot.json
│           └── version.json
└── published/
    └── <namespace>/<job>/
        └── current.json
```

---

# 74. Pourquoi séparer `versions/` et `published/`

`versions/` contient l'historique immuable.

`published/` contient la référence mutable :

```text
current → version immuable
```

Cela donne :

```text
history immutable
current pointer mutable atomically
```

---

# 75. `PublishedDataset`

Modèle conceptuel :

```python
@dataclass(frozen=True, slots=True)
class PublishedDataset:
    dataset_id: str
    version_id: str
    fingerprint: DatasetFingerprint
    snapshot_path: str
    published_at: datetime
    published_from_run_id: str
```

Il représente :

> **la version canonique actuellement consommable**

et non :

> le dernier run ayant réussi.

---

# 76. Run réussi ≠ publication

Un run peut être :

```text
SUCCESS
```

sans modifier la version publiée.

Exemples :

- run d'analyse ;
- dry run ;
- diff trop important ;
- version identique ;
- publication explicitement désactivée.

---

# 77. Publication atomique du pointeur

Le fichier :

```text
published/<dataset>/current.json
```

est écrit via une stratégie `temp + os.replace`, réutilisant `AtomicPublisher` ou une primitive équivalente.

Il ne doit jamais être visible à moitié écrit.

---

# 78. Ordre de publication

Séquence recommandée :

```text
1. validation réussie
2. fingerprint calculé
3. snapshot version durable
4. diff calculé
5. diff guard éventuel réussi
6. current.json écrit atomiquement
7. metadata publication enregistrée
8. events publiés
```

---

# 79. Source de vérité du published pointer

V0.4 ne peut pas faire une transaction distribuée entre :

```text
filesystem
+
SQLite/PostgreSQL metadata
```

Décision proposée :

> **Le fichier atomique `current.json` est la source de vérité de la version publiée filesystem V0.4. La metadata est un index opérationnel reconstructible.**

C'est plus sûr qu'une ambiguïté non documentée.

---

# 80. Publication identique

Si le candidat a le même fingerprint que le published courant :

```text
new version bytes       non nécessaires
pointer update          non nécessaire
publication             NO-OP explicite
```

Événement proposé :

```text
DATASET_PUBLICATION_SKIPPED_IDENTICAL
```

Le run reste un succès.

---

# 81. Publication et historique

Publier une version ne doit jamais supprimer l'ancienne.

```text
versions/v1  immutable
versions/v2  immutable
published/current → v2
```

L'historique permet inspection et rollback futur.

---

# 82. Rollback

Le modèle V0.4 doit rendre possible un rollback futur en repointant `current.json` vers une version existante.

Mais une commande de rollback riche n'est pas nécessaire pour le MVP V0.4.

Le store peut exposer une primitive de promotion d'une version existante ; une UX dédiée pourra être ajoutée après usage réel.

---

# 83. Concurrence de publication

V0.4 suppose :

```text
single writer per dataset_id
```

au moment de la promotion.

`os.replace()` garantit l'atomicité du fichier, mais pas une politique de résolution de deux promotions concurrentes.

Un lock distribué ou CAS multi-backend est hors V0.4.

L'orchestrateur externe doit éviter les runs concurrents du même dataset lorsque la publication est activée.

---

# 84. Version metadata SQL

Tables additives proposées :

```text
dataset_versions
----------------
dataset_id
version_id
fingerprint
snapshot_path
created_from_run_id
job_id
job_version
source_artifact_id
source_raw_sha256
created_at

UNIQUE(dataset_id, version_id)
```

et :

```text
dataset_version_runs
--------------------
dataset_id
version_id
run_id
created_at

UNIQUE(dataset_id, version_id, run_id)
```

---

# 85. Published metadata SQL

Table :

```text
published_datasets
------------------
dataset_id PK
version_id
published_from_run_id
published_at
```

La table permet des requêtes rapides mais ne remplace pas `current.json` comme source de vérité filesystem.

---

# 86. Compatibilité avec `publications`

La table V0.3 `publications` existe déjà.

V0.4 peut continuer à y écrire une ligne de compatibilité :

```text
dataset_id
status
candidate_path
published_path
published_at
```

La nouvelle table `published_datasets` ajoute l'identité de version sans casser l'ancien modèle.

---

# 87. Replay : définition

Un replay est :

> **un nouveau run qui réutilise un ou plusieurs RAW artifacts d'un run précédent au lieu de réacquérir les données externes.**

Il ne modifie jamais le run d'origine.

---

# 88. Replay ≠ retry

Un retry HTTP :

```text
même run
même acquisition
nouvel essai réseau
```

Un replay :

```text
nouveau run
aucun nouvel appel source
RAW historique réutilisé
lineage explicite
```

---

# 89. Commande cible

```bash
pyingest replay <run_id>
```

Options proposées :

```text
--param key=value
--allow-version-change
--no-verify
--workspace ...
--metadata-dsn ...
```

Ne pas multiplier les options en Alpha.

---

# 90. Précondition de replay

Un run est rejouable lorsque :

- le job est toujours disponible dans le registry ;
- au moins un RAW utile est encore accessible ;
- les paramètres non secrets nécessaires sont disponibles ou fournis ;
- les étapes d'acquisition utilisent une source compatible replay ou un contrat explicite ;
- le snapshot/fingerprint attendu est disponible si on demande une vérification exacte.

---

# 91. Replay des runs V0.2/V0.3

La V0.4 doit essayer de rejouer les anciens runs lorsque leurs RAW existent.

Mais certaines métadonnées de reproductibilité ajoutées en V0.4 n'existent pas historiquement.

Donc deux niveaux :

```text
pre-V0.4 run → best-effort replay
V0.4+ run    → full replay lineage / verification
```

---

# 92. RunContext replay

Extension additive proposée :

```python
@dataclass(slots=True)
class RunContext:
    ...
    replay: ReplayContext | None = None
```

Le défaut `None` préserve tous les jobs V0.3.

---

# 93. ReplayContext

Proposition :

```python
@dataclass(frozen=True, slots=True)
class ReplayContext:
    source_run_id: str
    source_job_id: str
    source_job_version: str
    raw_artifacts: tuple[ReplayRawArtifact, ...]
    verify_expected_fingerprint: str | None
```

Le contexte ne doit pas contenir les bytes eux-mêmes.

---

# 94. ReplayRawArtifact

Structure :

```text
origin_artifact_id
artifact_name
origin_path
source_uri
content_type
sha256
resolved_url
status_code
etag
last_modified
```

Cette donnée permet de sélectionner et matérialiser le RAW sans toucher à la source externe.

---

# 95. Matching RAW

Les sources framework doivent pouvoir retrouver un RAW historique à partir de :

```text
artifact_name
+
source_uri attendu
```

L'`artifact_name` est important car une URL peut produire plusieurs assets ou une même URL peut être utilisée plusieurs fois dans des étapes distinctes.

---

# 96. HTTP replay

`HttpSource.fetch(context)` doit commencer par :

```text
if replay context has matching RAW:
    materialize historical RAW
    return RawArtifact
else:
    perform normal HTTP fetch
```

En mode replay strict, l'absence de RAW doit être une erreur ; il ne faut pas tomber silencieusement vers Internet.

---

# 97. LocalSource replay

Même principe :

```text
replay mode
→ ne pas relire le fichier local courant
→ utiliser les bytes du RAW historique
```

Cela protège contre un fichier local qui aurait changé depuis le run d'origine.

---

# 98. Replay strict

Décision :

```text
replay command = strict by default
```

Si un RAW attendu n'est pas trouvé :

```text
ReplayError
```

Pas de fallback live automatique.

Un replay qui contacte la source sans le dire n'est pas un replay fiable.

---

# 99. Matérialisation dans le nouveau run

Le replay doit créer un nouveau RAW artifact dans le nouveau run.

```text
origin RAW
   │
   ├── bytes identiques
   │
   ▼
new run RAW
```

Pourquoi copier/réécrire plutôt que référencer directement ?

- run self-contained ;
- logique ArtifactStore simple ;
- pas de références cross-run fragiles ;
- compatible futurs stores.

Un content-addressable store pourra optimiser cela plus tard.

---

# 100. SHA-256 de replay

Le nouveau RAW doit vérifier :

```text
new_raw.sha256 == origin_raw.sha256
```

Sinon :

```text
ReplayIntegrityError
```

---

# 101. Provenance replay

Le nouveau RAW conserve les informations de source d'origine lorsqu'elles sont sûres :

```text
source_uri
content_type
resolved_url
status_code
etag
last_modified
```

Mais la lineage doit indiquer explicitement :

```text
acquisition_mode = REPLAY
origin_run_id
origin_artifact_id
origin_retrieved_at
```

afin de ne pas faire croire qu'un nouvel HTTP 200 a eu lieu.

---

# 102. Replay metadata table

Table additive :

```text
replay_runs
-----------
run_id PK
source_run_id
source_job_id
source_job_version
executed_job_version
verification_mode
expected_fingerprint
actual_fingerprint
status
created_at
```

---

# 103. Run reproducibility metadata

La V0.4 doit commencer à capturer les éléments utiles au replay futur qui ne sont pas encore structurés.

Table additive proposée :

```text
run_reproducibility
-------------------
run_id PK
framework_version
as_of
parameters_fingerprint
created_at
```

Les paramètres restent dans `runs.parameters_json` selon le contrat existant.

---

# 104. `as_of`

`RunContext.as_of` existe déjà mais n'est pas un champ dédié du `RunRecord` V0.3.

V0.4 doit le conserver pour les nouveaux runs afin qu'un replay puisse restaurer la date logique d'exécution lorsque le job l'utilise.

---

# 105. Paramètres et secrets

Le MetadataStore V0.3 redacted les paramètres sensibles.

Un replay ne peut donc pas "récupérer" un secret supprimé de l'historique — et c'est une bonne propriété de sécurité.

Pour un secret nécessaire à une étape downstream :

```bash
pyingest replay <run_id> --param api_token=...
```

ou équivalent via config/env.

---

# 106. Replay et acquisition secrets

Dans le cas typique :

```text
API token uniquement nécessaire pour FETCH
```

le replay n'en a pas besoin puisque FETCH utilise le RAW historique.

C'est précisément un des bénéfices de la boundary RAW.

---

# 107. Job version lors du replay

Par défaut, le replay doit exiger :

```text
installed job version == source job version
```

pour une vérification reproductible stricte.

---

# 108. `--allow-version-change`

Il est utile de pouvoir rejouer un ancien RAW avec une nouvelle version du job afin d'évaluer un changement de parser/normalizer.

Commande :

```bash
pyingest replay <run_id> --allow-version-change
```

Dans ce mode :

- la lineage enregistre old/new job versions ;
- une différence de fingerprint n'est pas automatiquement considérée comme un bug ;
- le diff par rapport à la version d'origine devient particulièrement utile.

---

# 109. Replay verification

Lorsqu'un fingerprint attendu existe :

```text
same RAW
+
same job version
+
same parameters
+
same as_of
        ↓
expected same Dataset fingerprint
```

Le replay peut vérifier cela automatiquement.

---

# 110. ReplayMismatch

Si le mode strict attend le même fingerprint et obtient un autre :

```text
ReplayMismatchError
```

Le run doit conserver tous ses artefacts/rapports avant de signaler l'échec, afin de permettre l'analyse.

---

# 111. `--no-verify`

Option utile pour un replay exploratoire :

```bash
pyingest replay <run_id> --no-verify
```

Le replay est exécuté mais aucune égalité de fingerprint n'est exigée.

La lineage indique clairement :

```text
verification_mode = NONE
```

---

# 112. Replay et code externe non déterministe

Le framework ne peut garantir l'idempotence si un job contient :

```text
random.random()
datetime.now() dans normalisation
appel API downstream
lecture d'un fichier externe non capturé
requête DB mutable
```

La V0.4 doit documenter la différence entre :

```text
replay support
```

et :

```text
replay determinism
```

---

# 113. Replay et side effects

Le replay ne doit pas automatiquement republier ou recharger un dataset dans des targets externes.

Recommandation V0.4 :

```text
replay defaults to publication disabled
```

ou impose une étape/option explicite pour republisher.

Cela évite qu'un diagnostic rejoué modifie l'état canonique.

---

# 114. Replay fixture mode

`fixture_mode` reste distinct de `replay`.

```text
fixture → source synthétique/déterministe fournie par job
replay  → RAW historique réel réutilisé
```

Ne pas fusionner les deux concepts.

---

# 115. Replay events

Événements proposés :

```text
REPLAY_STARTED
RAW_REPLAYED
REPLAY_VERIFICATION_COMPLETED
REPLAY_COMPLETED
```

Pas d'événement par ligne.

---

# 116. Manifest replay

Le manifest peut gagner une section additive :

```json
{
  "replay": {
    "source_run_id": "...",
    "source_job_version": "1.2.0",
    "executed_job_version": "1.2.0",
    "verification_mode": "STRICT",
    "expected_fingerprint": "sha256-...",
    "actual_fingerprint": "sha256-...",
    "matched": true
  }
}
```

---

# 117. Manifest versioning

Le manifest peut référencer les versions produites :

```json
{
  "dataset_versions": [
    {
      "dataset_id": "public.postal_codes",
      "version_id": "sha256-...",
      "snapshot_path": "..."
    }
  ]
}
```

Pas besoin d'embarquer le snapshot.

---

# 118. Événements versioning

Événements :

```text
DATASET_FINGERPRINTED
DATASET_VERSION_CREATED
DATASET_VERSION_REUSED
DATASET_PUBLISHED
DATASET_PUBLICATION_SKIPPED_IDENTICAL
```

Payloads sans données métier brutes.

---

# 119. CLI V0.4 — philosophie

La CLI doit rester orientée opérateur et inspectable.

Pas de mini-Git complet.

Commandes proposées :

```text
pyingest diff
pyingest versions
pyingest published
pyingest replay
```

---

# 120. `pyingest versions`

Exemple :

```bash
pyingest versions public.postal_codes
```

Sortie :

```text
VERSION ID              CREATED               RUN        PUBLISHED
sha256-a1...             2026-09-01T...        8c91...    no
sha256-b2...             2026-09-04T...        af10...    yes
```

---

# 121. `pyingest published`

```bash
pyingest published public.postal_codes
```

Affiche :

```text
dataset_id
version_id
fingerprint
published_at
published_from_run_id
snapshot_path
```

---

# 122. `pyingest diff`

Après B1, forme proposée :

```bash
pyingest diff <candidate-run-id> --against published
```

ou :

```bash
pyingest diff --dataset public.postal_codes --from <version-a> --to <version-b>
```

Ne pas figer les deux syntaxes avant de tester l'ergonomie réelle.

---

# 123. `pyingest replay`

```bash
pyingest replay 8983404b
```

La CLI :

1. résout le run ;
2. retrouve le job ;
3. charge ses RAW ;
4. vérifie la compatibilité de version ;
5. crée un nouveau run ;
6. désactive la source live ;
7. exécute ;
8. compare le fingerprint si disponible ;
9. affiche la lineage.

---

# 124. Status V0.4

`pyingest status <run-id>` doit pouvoir montrer :

```text
Diff reports
Dataset versions
Replay source run
Replay verification
Publication version
```

sans obliger l'opérateur à ouvrir SQLite.

---

# 125. API de versioning proposée

Exemple :

```python
from pyingestkit.versioning import FilesystemDatasetVersionStore

store = FilesystemDatasetVersionStore(workspace)

version = store.create_version(
    dataset,
    dataset_id="public.postal_codes",
    context=context,
)

published = store.publish(version)
```

---

# 126. API de diff + published

Exemple :

```python
current = store.get_published("public.postal_codes")
previous = store.load_dataset(current.version_id)

policy = DiffPolicy(
    key_fields=("postal_code", "commune"),
    ignore_fields=("source_updated_at",),
)

diff = DatasetDiffer(policy).compare(previous, candidate)
```

---

# 127. API replay proposée

Éviter que chaque job construise son propre replay engine.

Service conceptuel :

```python
ReplayService(
    registry=job_registry,
    metadata_store=metadata,
    artifact_store=artifact_store,
).replay(run_id)
```

Le CLI l'utilise.

---

# 128. Replay source integration

Le `ReplayService` ne doit pas reconstruire une pipeline différente.

Il doit exécuter **le même Job/Pipeline**, mais avec un `RunContext` replay-aware.

C'est essentiel pour tester la vraie reproductibilité du code.

---

# 129. Limite aux sources framework

V0.4 garantit le replay automatique pour :

```text
HttpSource
LocalSource
```

et toute future Source qui implémente le contrat replay-aware.

Un job qui réalise directement :

```python
requests.get(...)
```

à l'intérieur d'un `Step` n'est pas automatiquement rejouable.

C'est une boundary assumée.

---

# 130. Source protocol future

La V0.4 peut formaliser une capability :

```text
ReplayAwareSource
```

mais doit éviter de casser le `Source` abstrait existant.

Préférer un helper/contexte que les sources officielles utilisent plutôt qu'une nouvelle méthode abstraite obligatoire.

---

# 131. Error hierarchy

Ajouter seulement les exceptions utiles :

```text
DiffError
SnapshotError
VersioningError
ReplayError
ReplayIntegrityError
ReplayMismatchError
```

Elles héritent de `PyIngestKitError` / `IngestionError` selon la hiérarchie existante.

Ne pas créer une exception par micro-cas.

---

# 132. Backend exceptions

Le snapshot/version store doit wrapper :

```text
OSError
JSONDecodeError
```

Le replay doit wrapper les erreurs de résolution spécifiques, tout en conservant `raise ... from exc`.

---

# 133. Sécurité — diff reports

Les diff reports ne doivent pas devenir un exfiltration channel.

Par défaut :

```text
counts              oui
keys                oui, bounded/redacted si sensibles
changed field names oui
full before/after   non
```

---

# 134. Sécurité — clés sensibles

Une `key_field` peut elle-même contenir une donnée sensible.

La représentation report/log doit passer par une fonction de preview/redaction commune.

Le moteur in-memory peut conserver la valeur réelle pour comparer.

---

# 135. Sécurité — snapshots

Les snapshots contiennent les valeurs réelles.

Ils doivent être traités comme des données, pas comme des logs.

Le framework doit :

- utiliser les permissions de workspace existantes ;
- empêcher path traversal ;
- écrire atomiquement ;
- ne jamais uploader automatiquement ;
- documenter la sensibilité.

---

# 136. Sécurité — replay

Replay ne doit jamais restaurer :

```text
Authorization
Cookie
API token
password
```

à partir de logs ou metadata redacted.

Il réutilise les bytes RAW capturés, pas les secrets d'acquisition.

---

# 137. Path traversal

`dataset_id`, `version_id`, `run_id` et `artifact_name` doivent être normalisés/validés avant construction des chemins.

Aucun :

```text
../../
absolute path injection
```

---

# 138. Snapshot corruption

Lors du chargement d'une version :

1. lire `version.json` ;
2. lire `dataset.snapshot.json` ;
3. recalculer le fingerprint ;
4. vérifier qu'il correspond à `version_id`.

Une divergence est une corruption, pas un nouveau diff.

---

# 139. Version immutability

Une version existante :

```text
sha256-X
```

ne doit jamais être écrasée par un contenu différent.

Si le path existe :

- charger metadata ;
- vérifier fingerprint ;
- réutiliser si identique ;
- erreur si incohérent.

---

# 140. Atomic snapshot creation

Créer une version :

```text
write temp directory/files
verify snapshot fingerprint
atomic promote directory or final files
```

Sur un seul filesystem, utiliser des primitives atomiques autant que possible.

---

# 141. Partial version recovery

Si un crash laisse un temp file :

```text
.version.<uuid>.tmp
```

il ne doit jamais être considéré comme une version valide.

Le listing ignore les temporaires.

---

# 142. Version listing

`list_versions(dataset_id)` doit lire prioritairement la metadata officielle du store et/ou les `version.json` valides.

Un dossier orphelin sans metadata valide ne doit pas apparaître comme version publiée.

---

# 143. Metadata rebuild future

Puisque `current.json` et `version.json` sont des preuves persistées, il doit rester possible de reconstruire une partie de la metadata SQL en cas de perte.

V0.4 n'a pas besoin d'une commande `reindex`, mais le format ne doit pas la rendre impossible.

---

# 144. Reproductibilité du snapshot

Pour le même Dataset et le même `snapshot_version` :

```text
snapshot logical content identical
```

Les timestamps de provenance doivent rester dans `version.json`, pas dans `dataset.snapshot.json`, afin que le snapshot de contenu reste déterministe.

---

# 145. Snapshot et ordre des lignes

Le snapshot doit préserver l'ordre original du Dataset pour permettre un round-trip fidèle.

Le fingerprint peut être order-insensitive selon sa policy.

Cette distinction est importante :

```text
snapshot = fidélité
fingerprint = identité selon policy
```

---

# 146. Diff et fingerprint policy

Un `DatasetDiff` doit indiquer la policy de fingerprint utilisée pour éviter une ambiguïté.

Par exemple :

```text
order_sensitive=False
canonical_version=1
```

---

# 147. Canonical codec version

La canonicalisation doit avoir une version interne stable :

```text
canonical_version = "1"
```

Un changement futur de codec ne doit pas silently modifier tous les fingerprints existants.

---

# 148. Migration de codec future

Si un jour `canonical_version=2` devient nécessaire :

- conserver la capacité de lire v1 ;
- ne pas renommer les anciennes versions ;
- calculer explicitement le nouvel ID si migration désirée ;
- documenter l'incompatibilité.

---

# 149. Job version et version de dataset

Une nouvelle job version peut produire le même Dataset version.

Exemple :

```text
job 1.1.0 → sha256-A
job 1.2.0 → sha256-A
```

Cela signifie :

```text
code changed
logical output unchanged
```

Information très utile pour le replay et la non-régression.

---

# 150. Dataset version et provenance

Une DatasetVersion doit pouvoir remonter à :

```text
version_id
  ↓
run_id(s)
  ↓
raw artifact(s)
  ↓
source provenance
```

C'est la chaîne de preuve principale de V0.4.

---

# 151. Quality linkage

`version.json` peut référencer les quality reports du run :

```text
validation report path
profile report path
diff report path
```

Il ne doit pas copier tout leur contenu.

---

# 152. Publication condition

La publication standard devrait exiger :

```text
run success
AND
no ERROR validation
AND
diff guard passed if configured
AND
snapshot verified
```

Le framework ne doit pas publier un dataset invalide.

---

# 153. Diff baseline default

Pour un dataset déjà publié :

```text
baseline = PublishedDataset current version
```

Pour le tout premier run :

```text
no baseline
```

Le diff peut retourner une notion :

```text
INITIAL
```

ou simplement traiter toutes les lignes comme `ADDED`.

Recommandation : toutes les lignes `ADDED`, `previous_version_id=None`.

---

# 154. First publication

Première version :

```text
previous = empty Dataset with compatible schema / no baseline marker
candidate = current Dataset
```

Rapport :

```text
added = row_count
removed = 0
changed = 0
initial = true
```

---

# 155. Schema-only change

Si les lignes n'ont pas changé mais le schéma oui :

```text
schema changed = true
```

Le fingerprint change nécessairement si le schéma fait partie de l'identité.

Le diff guard peut décider de bloquer.

---

# 156. Column order change

Le Dataset conserve un ordre de champs.

Le diff de schéma doit pouvoir signaler :

```text
field_order_changed
```

La policy peut décider si cet ordre compte pour le fingerprint.

Recommandation : oui pour le schéma de snapshot, mais la documentation doit préciser ce choix.

---

# 157. Changed fields et schema addition

Si un champ est ajouté, il n'est pas nécessaire de créer un `CHANGED` pour chaque ligne si cela rend le rapport inutilisable.

Recommandation :

- reporter le changement dans `SchemaDiff` ;
- pour row diff, comparer les champs communs/explicitement comparés ;
- une option `schema_changes_affect_rows` peut être évitée en V0.4 pour garder une règle simple.

La règle finale doit être figée en A1.

---

# 158. Décision recommandée sur schema addition

Pour V0.4-a1 :

```text
SchemaDiff signale les colonnes ajoutées/supprimées.
Row-level CHANGED compare les champs comparables présents dans les deux schémas,
plus les compare_fields explicites lorsqu'elles existent.
```

Cela évite un million de `CHANGED` lors de l'ajout d'une colonne nullable.

---

# 159. Suppression d'un champ significatif

Si `compare_fields` contient un champ supprimé du candidat ou de la baseline :

```text
DiffError / schema policy violation
```

Ne pas l'ignorer silencieusement.

---

# 160. Key field schema change

Si une clé disparaît :

```text
DiffError
```

Le moteur ne peut plus aligner les lignes.

---

# 161. Dataset ID version contract

Le `dataset_id` doit être stable dans le temps.

Renommer :

```text
public.postal_codes
→ public.fr_postal_codes
```

crée conceptuellement une autre série de versions sauf migration explicite.

Le framework ne doit pas deviner qu'il s'agit du même dataset.

---

# 162. Version branches

V0.4 n'introduit pas de branches de datasets.

Un `dataset_id` possède :

```text
N versions historiques
1 published current maximum
```

Pas de :

```text
dev branch
staging branch
merge branch
```

Les environnements restent gérés par workspace/config/orchestrateur.

---

# 163. Version tags métier

Un projet peut vouloir :

```text
2026-Q3
PCG-2026
NAF-2025
```

V0.4 ne doit pas confondre cela avec `version_id`.

Un label métier optionnel pourra être porté dans metadata :

```text
label / external_version
```

mais le content identity reste le fingerprint.

---

# 164. Publication state

Statuts génériques proposés :

```text
CANDIDATE
PUBLISHED
SUPERSEDED
```

Mais il peut être plus simple de dériver `SUPERSEDED` de la version courante plutôt que de muter toutes les anciennes rows.

Recommandation : garder les versions immuables et un pointeur published séparé.

---

# 165. Version store et ArtifactStore

Le DatasetVersionStore peut réutiliser des primitives d'ArtifactStore pour JSON atomique, mais il a une responsabilité différente :

```text
ArtifactStore      → artefacts de run
DatasetVersionStore→ historique cross-run du Dataset
```

Ne pas tout mélanger dans `ArtifactStore`.

---

# 166. Pourquoi un store dédié

Le lifecycle d'un snapshot versionné est différent :

```text
run artifact
  peut être temporaire / lié au run

version snapshot
  doit survivre au run et rester immuable
```

Un store dédié rend cette distinction explicite.

---

# 167. Future object storage

L'API `DatasetVersionStore` doit rester compatible avec une future implémentation S3/MinIO, mais V0.4 n'en implémente aucune.

Éviter des méthodes qui supposent :

```text
Path local partout
```

dans le contrat public, même si l'implémentation filesystem utilise `Path` en interne.

---

# 168. URI de snapshot

Dans les modèles publics, préférer :

```text
snapshot_uri
```

ou un `str` abstrait plutôt qu'un `Path` obligatoire si l'on veut préparer les stores distants.

Dans V0.4 filesystem :

```text
file:///...
```

ou un path relatif contrôlé.

Le choix exact doit être cohérent avec les artefacts V0.3.

---

# 169. Snapshot load contract

```python
version = store.get_version(dataset_id, version_id)
dataset = store.load_dataset(version)
```

Le retour reste `Dataset`, jamais DataFrame.

---

# 170. Report schemas indépendants

V0.4 ajoute au minimum :

```text
diff report_version = 1
snapshot_version    = 1
version_schema      = 1
replay schema       = 1
```

Ces versions ne doivent pas être liées automatiquement à 0.4.0.

---

# 171. Public API package layout

Proposition :

```text
src/pyingestkit/
├── diff/
│   ├── __init__.py
│   ├── models.py
│   ├── policy.py
│   ├── engine.py
│   └── report.py
│
├── versioning/
│   ├── __init__.py
│   ├── canonical.py
│   ├── fingerprint.py
│   ├── snapshot.py
│   ├── models.py
│   ├── base.py
│   └── filesystem.py
│
├── replay/
│   ├── __init__.py
│   ├── models.py
│   ├── resolver.py
│   └── service.py
│
└── cli/commands/
    ├── diff.py
    ├── versions.py
    ├── published.py
    └── replay.py
```

---

# 172. `diff` namespace

API publique principale :

```text
DiffPolicy
DatasetDiffer
DatasetDiff
DiffEntry
DiffKind
SchemaDiff
```

Éviter d'exposer les helpers d'index/canonicalisation.

---

# 173. `versioning` namespace

API publique principale :

```text
DatasetFingerprint
DatasetFingerprintPolicy
DatasetFingerprinter
DatasetVersion
PublishedDataset
DatasetVersionStore
FilesystemDatasetVersionStore
```

Le `SnapshotCodec` peut rester public namespaced si les packs ont un besoin légitime d'inspection, mais ne doit pas nécessairement être top-level.

---

# 174. `replay` namespace

API :

```text
ReplayContext
ReplayResult
ReplayService
```

Les détails `ReplayRawResolver` restent internes si possible.

---

# 175. Top-level imports

Ne pas automatiquement exporter 20 nouveaux symboles depuis :

```python
import pyingestkit
```

Recommandation : top-level seulement les primitives principales les plus utilisées.

Les modèles spécialisés restent namespaced.

---

# 176. Type hints

V0.4 doit rester compatible Mypy strict.

Les valeurs canoniques peuvent nécessiter des `TypeAlias` dédiés pour éviter un `Any` omniprésent.

Exemple :

```python
CanonicalScalar = None | bool | int | float | str
```

avec structures tagged explicites.

---

# 177. Immutabilité des preuves

Doivent être immuables :

```text
DatasetFingerprint
DiffPolicy
DatasetDiff
DiffEntry
SchemaDiff
DatasetVersion
PublishedDataset
ReplayResult
```

Utiliser :

```python
@dataclass(frozen=True, slots=True)
```

lorsque adapté.

---

# 178. Version store mutable

Le store/service lui-même est évidemment opérationnel/mutable.

Ne pas confondre :

```text
immutable evidence models
vs
mutable infrastructure services
```

---

# 179. Logging

Logs V0.4 utiles :

```text
run_id
job_id
dataset_id
version_id
previous_version_id
candidate_fingerprint
added_count
removed_count
changed_count
replay_source_run_id
replay_matched
```

Jamais :

```text
full row
full snapshot
Authorization
secret params
```

---

# 180. Metrics

Sans introduire Prometheus :

```text
diff_added_rows
diff_removed_rows
diff_changed_rows
diff_unchanged_rows
dataset_versions_created
replay_raw_bytes
replay_verified
```

Peuvent être présents dans Step metrics/events.

---

# 181. Tests — philosophie

Tous les tests ordinaires restent :

```text
offline
déterministes
tempfile-based
sans service externe
```

Le replay doit être prouvé avec socket bloqué.

---

# 182. Tests fingerprint

Couverture minimale :

```text
same dataset → same fingerprint
row reorder invariant by default
order_sensitive=True detects reorder
field order semantics documented
nested dict order invariant
bool vs int distinct
int vs float distinct
Decimal exact
bytes round-trip
datetime timezone preserved
NaN stable
unsupported type fails
no mutation
```

---

# 183. Tests keyed diff

```text
added
removed
changed
unchanged
composite key
ignore_fields
compare_fields
duplicate previous key
duplicate candidate key
null key
missing key
missing vs None
nested values
schema changes
max_entries
stable ordering
no mutation
```

---

# 184. Tests keyless diff

```text
added row
removed row
duplicate row multiplicity
reordered rows
nested unhashable rows
changed_count always 0
```

---

# 185. Tests snapshot

```text
round-trip empty Dataset
round-trip fields
round-trip sparse rows
None/bool/int/float/str
bytes
Decimal
date/datetime
list/tuple
nested mapping
unsupported value failure
corruption detection
fingerprint verification
atomic write
no pickle
```

---

# 186. Tests version store

```text
create first version
reuse identical version
create second changed version
list versions
load version
publish current
atomic pointer
published survives later failed run
identical publication no-op
invalid snapshot rejected
path traversal blocked
```

---

# 187. Tests metadata additive schema

Sur une SQLite V0.3 existante :

```text
open with V0.4
create new tables
retain old runs
retain old artifacts
retain old validations
retain old publications
```

Aucune migration destructive.

---

# 188. Tests replay HTTP

Scénario critique :

```text
1. run demo.http_csv in fixture transport
2. capture RAW
3. patch socket.connect to raise
4. replay original run
5. verify replay succeeds
6. verify no transport call
7. verify RAW sha256 identical
8. verify lineage recorded
```

---

# 189. Tests replay LocalSource

```text
1. ingest local file A
2. modify/delete original local file
3. replay
4. replay succeeds from RAW
5. output matches original fingerprint
```

Cela prouve que replay ≠ relire la source actuelle.

---

# 190. Tests replay mismatch

```text
same RAW
+
changed job logic
+
--allow-version-change or simulated version
→ different fingerprint
```

Le test doit vérifier :

- lineage old/new ;
- mismatch observable ;
- pas de corruption du run original.

---

# 191. Tests release wheels

Le wheel smoke V0.4 doit continuer à installer :

```text
framework wheel
excel/parquet extras
demo job wheel
```

puis exécuter :

- les 6 jobs V0.3 ;
- le job versioned de référence V0.4 ;
- une séquence replay offline.

---

# 192. Reference job V0.4

Proposition :

```text
demo.versioned_ndjson
```

Paramètre :

```text
revision=1 | 2
```

---

# 193. `demo.versioned_ndjson` revision 1

Fixture :

```json
{"id": 1, "name": "A"}
{"id": 2, "name": "B"}
```

Pipeline :

```text
Fetch fixture
→ Parse NDJSON
→ Validate
→ Profile
→ Fingerprint
→ Snapshot/version
→ Initial diff
→ Publish
```

---

# 194. `demo.versioned_ndjson` revision 2

Fixture :

```json
{"id": 1, "name": "A2"}
{"id": 3, "name": "C"}
```

Diff attendu contre revision 1 :

```text
added   id=3
removed id=2
changed id=1 name
```

C'est une preuve E2E idéale.

---

# 195. E2E replay du job versioned

Après publication de revision 2 :

```text
replay run revision 2 from RAW
        ↓
no source call
        ↓
same fingerprint
        ↓
verification PASS
```

Le replay ne doit pas republier automatiquement.

---

# 196. Non-régression V0.3

À chaque jalon V0.4, les jobs suivants restent verts :

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

---

# 197. Python support

Conserver :

```text
Python 3.11
Python 3.12
Python 3.13
```

Aucune dépendance V0.4 ne justifie de réduire cette matrice.

---

# 198. Dépendances

Objectif :

```text
aucune nouvelle dépendance runtime obligatoire
```

La canonicalisation, le snapshot JSON, le diff, le registry filesystem et le replay doivent être faisables avec la stdlib et les dépendances déjà présentes.

---

# 199. Pas de deepdiff

Ne pas ajouter `deepdiff` ou équivalent uniquement pour comparer des rows.

Le framework a besoin d'une sémantique plus spécifique :

- keyed diff ;
- sparse rows ;
- type-aware values ;
- bounded reports ;
- schema diff ;
- deterministic ordering.

Une petite implémentation dédiée est plus appropriée.

---

# 200. Pas de DVC

DVC résout un autre problème : versionner de gros artefacts/data dans un workflow Git/remote.

PyIngestKit V0.4 a besoin d'un historique opérationnel local/plug-in aware lié aux runs et RAW.

Pas de dépendance DVC.

---

# 201. Pas de LakeFS

LakeFS fournit des branches/commits sur object storage.

Ce n'est pas le scope de PyIngestKit V0.4.

Interop future possible, mais pas de réimplémentation.

---

# 202. Pas de Delta/Iceberg

Ces formats gèrent le versioning transactionnel de tables/lakes à grande échelle.

PyIngestKit reste un ingestion framework générique et engine-neutral.

V0.5 targets pourront charger vers de tels systèmes via adapters externes si besoin réel.

---

# 203. Performance — fingerprint

Le fingerprint order-insensitive peut nécessiter un tri de représentations canoniques :

```text
O(n log n)
```

sous la boundary materialized Dataset.

C'est acceptable en V0.4 pour des datasets bornés.

---

# 204. Performance — diff

Le keyed diff devrait éviter de reconstruire plusieurs copies des rows.

Préférer :

```text
key → row reference/canonical comparison payload
```

et ne créer les `DiffEntry` qu'en cas de changement.

---

# 205. Performance — snapshot

L'écriture snapshot peut être streaming au niveau de l'encodeur JSON interne, mais le Dataset est déjà matérialisé.

Il n'est pas nécessaire d'introduire un streaming Dataset pour V0.4.

---

# 206. Performance — replay

Copier un RAW vers le nouveau run est un coût volontaire pour la simplicité et l'isolation.

Une future ArtifactStore content-addressed pourra dédupliquer physiquement sans changer l'API Replay.

---

# 207. Memory limits

Diff exact, distinct key index et snapshots restent destinés aux datasets bornés V0.3/V0.4.

Documenter clairement :

```text
V0.4 ≠ diff engine pour des tables de milliards de lignes
```

---

# 208. Future scalable diff

Un futur adapter pourrait comparer dans :

```text
DuckDB
Polars
Spark
warehouse SQL
```

mais cela doit être une capability séparée, pas un changement silencieux du core `DatasetDiffer`.

---

# 209. ADRs V0.4

Proposition :

```text
ADR-034 — Dataset fingerprint uses a versioned type-aware canonical representation
ADR-035 — Dataset diff is explicit, key-aware and deterministic
ADR-036 — Dataset snapshots use a safe JSON round-trip format; no pickle
ADR-037 — Dataset versions are content-addressed and immutable
ADR-038 — PublishedDataset is an atomic pointer to an immutable version
ADR-039 — Replay reuses historical RAW and never falls back to live acquisition silently
ADR-040 — V0.4 metadata evolves through additive capability tables
```

Numérotation à ajuster au repo réel avant création.

---

# 210. Documentation V0.4

Fichiers proposés :

```text
docs/architecture/diff-replay-versioning-v0.4.md

docs/guides/dataset-diff.md
docs/guides/dataset-versioning.md
docs/guides/published-dataset.md
docs/guides/replay-a-run.md

docs/guides/release-validation-v0.4.0.md
```

---

# 211. Alpha 1 — scope

`V0.4.0-a1 — Dataset Fingerprints + Diff Engine`

Implémenter uniquement :

```text
canonical value representation v1
DatasetFingerprintPolicy
DatasetFingerprinter
DiffPolicy
DatasetDiffer
DatasetDiff
DiffEntry
SchemaDiff
keyed diff
keyless multiset diff
max_entries
unit/contract tests
ADR-034/035
guide diff
```

---

# 212. Alpha 1 — hors scope

Ne pas implémenter encore :

```text
diff.json runtime report
metadata diff table
snapshot persistence
version registry
PublishedDataset
replay
CLI replay
```

---

# 213. Alpha 1 — Definition of Done

```text
same Dataset fingerprint deterministic
row-order policy tested
nested values stable
type-aware comparison
keyed added/removed/changed correct
keyless multiset correct
schema diff correct
duplicate keys rejected
missing/null semantics tested
max_entries bounded
no mutation
no new mandatory dependency
all V0.3 tests green
make verify green
```

---

# 214. Alpha 1 — archive

```text
pyingestkit-v0.4.0-a1-diff-engine.zip
```

---

# 215. Alpha 2 — scope

`V0.4.0-a2 — Diff Reports + Runtime / Metadata Observation`

Ajouter :

```text
diff report schema v1
reports/diff.json
Runner observation of DatasetDiff
manifest report refs
DIFF_* events
DiffMetadataCapability
dataset_diffs additive table
SQLite/Postgres built-in support
status visibility
security/redaction tests
ADR/report guide
```

---

# 216. Alpha 2 — Definition of Done

```text
diff report atomically written
report schema stable
counts exact
entries bounded
no raw row leak by default
manifest ref correct
events compact
built-in metadata queryable
custom legacy MetadataStore remains usable
V0.3 report behavior unchanged
make verify green
```

---

# 217. Alpha 2 — archive

```text
pyingestkit-v0.4.0-a2-diff-reports-runtime.zip
```

---

# 218. Beta 1 — scope

`V0.4.0-b1 — Dataset Snapshots + Version Registry + PublishedDataset`

Ajouter :

```text
snapshot JSON format v1
round-trip codec
DatasetVersion
DatasetVersionStore
FilesystemDatasetVersionStore
content-addressed version IDs
version.json
versions/ workspace
PublishedDataset
published/current.json
atomic publish pointer
version metadata tables
CLI versions/published
ADR-036/037/038
```

---

# 219. Beta 1 — Definition of Done

```text
snapshot all supported V0.3 value types
round-trip Dataset
snapshot fingerprint verified
unsupported types fail explicitly
same content reuses version
changed content creates version
history immutable
current pointer atomic
identical publish no-op
old published version retained
metadata additive
path traversal protected
make verify green
```

---

# 220. Beta 1 — archive

```text
pyingestkit-v0.4.0-b1-versioning-published.zip
```

---

# 221. Beta 2 — scope

`V0.4.0-b2 — Replay From RAW + Lineage`

Ajouter :

```text
ReplayContext
ReplayService
strict replay raw resolver
HttpSource replay support
LocalSource replay support
replay lineage metadata
run reproducibility metadata
replay manifest section
REPLAY_* events
CLI pyingest replay
same-version verification
--allow-version-change
--no-verify
ADR-039/040
guide replay
```

---

# 222. Beta 2 — Definition of Done

```text
HTTP replay makes zero network call
Local replay survives source deletion/change
new run gets new RAW artifact
RAW sha256 identical
origin lineage queryable
same-version replay fingerprint matches
mismatch detected
no live fallback
secret params not restored
pre-V0.4 replay best-effort documented
make verify green
```

---

# 223. Beta 2 — archive

```text
pyingestkit-v0.4.0-b2-replay-lineage.zip
```

---

# 224. RC1 — scope

`V0.4.0-rc1 — Diff / Replay / Versioning E2E`

Vertical slice :

```text
revision 1 RAW
  ↓
Dataset
  ↓
Validation + Profile
  ↓
Fingerprint
  ↓
Version 1
  ↓
Publish current

revision 2 RAW
  ↓
Dataset
  ↓
Fingerprint
  ↓
Diff against published V1
  ↓
diff report
  ↓
Version 2
  ↓
Publish current → V2

Replay revision 2 run
  ↓
reuse RAW
  ↓
no acquisition
  ↓
Fingerprint == V2
  ↓
verification PASS
```

---

# 225. RC1 — reference job

Ajouter :

```text
demo.versioned_ndjson
```

Le demo pack contient alors sept jobs.

Les six V0.3 restent inchangés conceptuellement.

---

# 226. RC1 — wheel smoke

Le smoke installé depuis wheels doit prouver :

```text
framework import
optional Excel/Parquet extras
7 job entry points
V0.3 six jobs success
versioned job revision 1 success
versioned job revision 2 success
diff.json created
versions list contains V1/V2
published points to V2
replay V2 success with network blocked
fingerprint verified
```

---

# 227. RC1 — Definition of Done

```text
full E2E green
all CLI contracts stable
SQLite metadata migration additive green
Postgres adapter contracts green
no custom MetadataStore regression
security gates green
pip-audit green
build green
wheel smoke green
Python 3.11/3.12/3.13 green
```

---

# 228. RC1 — archive

```text
pyingestkit-v0.4.0-rc1-diff-replay-versioning-e2e.zip
```

---

# 229. Stable V0.4.0 — scope

Stable = promotion du RC après hardening, pas ajout de features.

Actions :

```text
freeze API names
freeze canonical_version=1
freeze snapshot_version=1
freeze diff report_version=1
freeze CLI
README
CHANGELOG
ADRs
release validation guide
full release-check
wheel/sdist
checksums
GitHub release
```

---

# 230. Stable V0.4.0 — archive

```text
pyingestkit-v0.4.0.zip
```

---

# 231. Branch Git

Après fermeture officielle V0.3 :

```bash
git checkout main
git pull
git checkout -b feat/v0.4-diff-replay-versioning
```

---

# 232. Commit strategy

Commits cohérents :

```text
feat(diff): add canonical dataset fingerprinting
feat(diff): add keyed and keyless dataset diff engine
feat(diff): materialize runtime diff reports
feat(versioning): add safe dataset snapshot codec
feat(versioning): add filesystem version registry
feat(publication): add PublishedDataset atomic pointer
feat(replay): replay framework sources from historical raw
feat(replay): add CLI and lineage verification
feat(demo): add versioned NDJSON reference slice
docs(v0.4): finalize diff replay versioning release docs
```

---

# 233. Implementation lots

## Lot 0 — Baseline / freeze

- checkout main after V0.3 release ;
- assert `pyingest --version == 0.3.0` ;
- run `make release-check` ;
- record baseline commit/tag ;
- create branch V0.4.

## Lot 1 — canonical values

- canonical model ;
- tagged scalar encoder ;
- nested collections ;
- stable mapping order ;
- special floats ;
- supported type errors.

## Lot 2 — fingerprint

- policy ;
- field/schema input ;
- row-order handling ;
- SHA-256 ;
- immutable result ;
- tests.

## Lot 3 — DiffPolicy / models

- invariants ;
- key fields ;
- ignore/compare fields ;
- max_entries ;
- capture values ;
- schema diff model.

## Lot 4 — keyed diff

- index ;
- duplicate key failure ;
- null/missing key failure ;
- added/removed/changed ;
- deterministic order.

## Lot 5 — keyless diff

- canonical multiset ;
- duplicate multiplicity ;
- added/removed ;
- no changed semantics.

## Lot 6 — diff reports

- schema v1 ;
- safe entries ;
- report writer ;
- ArtifactStore integration ;
- manifest.

## Lot 7 — runtime observation

- `_dataset_diffs()` helper ;
- Runner integration ;
- events ;
- status.

## Lot 8 — diff metadata

- capability interface ;
- additive SQL table ;
- memory/SQLite/Postgres official adapters ;
- compatibility tests.

## Lot 9 — snapshot codec

- snapshot schema ;
- full round-trip ;
- no repr fallback ;
- corruption checks.

## Lot 10 — version store

- base contract ;
- filesystem implementation ;
- content-addressed directory ;
- version metadata ;
- dedup identical content.

## Lot 11 — published model

- `current.json` ;
- atomic pointer ;
- current resolver ;
- publication metadata compatibility ;
- identical no-op.

## Lot 12 — CLI versioning

- versions ;
- published ;
- JSON output ;
- prefix handling where safe.

## Lot 13 — replay context/resolver

- source run lookup ;
- raw selection ;
- strict mode ;
- raw materialization ;
- sha verification.

## Lot 14 — source replay integration

- HttpSource ;
- LocalSource ;
- no network fallback ;
- no local re-read.

## Lot 15 — replay service

- job resolution ;
- version compatibility ;
- parameters/as_of ;
- new run ;
- lineage ;
- verification.

## Lot 16 — CLI replay

- command ;
- output ;
- `--allow-version-change` ;
- `--no-verify` ;
- errors.

## Lot 17 — reference job

- versioned NDJSON revision 1/2 ;
- deterministic fixture ;
- diff/publish ;
- replay E2E.

## Lot 18 — hardening

- security ;
- corrupted snapshots ;
- path traversal ;
- metadata compatibility ;
- no data leak ;
- strict typing ;
- docs.

## Lot 19 — RC

- full matrix ;
- wheel smoke ;
- install from wheel only ;
- replay with socket blocked.

## Lot 20 — Stable

- version promotion ;
- final checksums ;
- release notes ;
- GitHub tag/release.

---

# 234. Stable issue/error vocabulary

Proposition d'erreurs textuelles / codes :

```text
diff.duplicate_key
diff.null_key
diff.missing_key
diff.schema_missing_key_field
diff.invalid_policy

snapshot.unsupported_type
snapshot.invalid_format
snapshot.fingerprint_mismatch

version.not_found
version.corrupt
version.publish_failed

replay.raw_not_found
replay.raw_ambiguous
replay.raw_hash_mismatch
replay.job_not_found
replay.job_version_mismatch
replay.output_mismatch
```

Les exceptions Python restent peu nombreuses ; ces codes peuvent apparaître dans les rapports/metadata.

---

# 235. Stable event vocabulary

Avant RC1, vérifier que les événements sont cohérents :

```text
DIFF_STARTED
DIFF_COMPLETED
DIFF_REPORT_WRITTEN

DATASET_FINGERPRINTED
DATASET_VERSION_CREATED
DATASET_VERSION_REUSED
DATASET_PUBLISHED
DATASET_PUBLICATION_SKIPPED_IDENTICAL

REPLAY_STARTED
RAW_REPLAYED
REPLAY_VERIFICATION_COMPLETED
REPLAY_COMPLETED
```

Éviter les synonymes.

---

# 236. Stable public naming

Noms recommandés :

```text
DatasetFingerprinter
DatasetFingerprint
DatasetFingerprintPolicy

DatasetDiffer
DiffPolicy
DatasetDiff
DiffEntry
DiffKind
SchemaDiff

DatasetVersion
DatasetVersionStore
FilesystemDatasetVersionStore
PublishedDataset

ReplayContext
ReplayResult
ReplayService
```

---

# 237. Noms à éviter

Éviter les doublons :

```text
DataDiff + DatasetDiff
DiffResult + DatasetDiff
VersionedDataset + DatasetVersion
CurrentDataset + PublishedDataset
ReplayRun + ReplayResult
SnapshotHash + DatasetFingerprint
```

Un seul terme public par concept.

---

# 238. `VersionedDataset` vs `DatasetVersion`

Recommandation :

```text
DatasetVersion
```

car l'objet représente une version persistée de contenu.

`VersionedDataset` pourrait laisser penser à un wrapper mutable autour du Dataset.

---

# 239. `PublishedDataset`

Conserver ce nom car il exprime précisément :

```text
la version canonique actuellement promue
```

et correspond à la vision initiale PyIngestKit.

---

# 240. Version publication et Quality

Le flux V0.4 complet recommandé est :

```text
Dataset
  ↓
Validate
  ↓
Profile
  ↓
Fingerprint
  ↓
Snapshot candidate
  ↓
Diff vs Published
  ↓
Diff Guard
  ↓
Create/Re-use Version
  ↓
Atomic Publish
```

Le profiling peut rester optionnel ; la validation bloquante reste prioritaire.

---

# 241. Pourquoi snapshot avant diff ou après diff ?

Le fingerprint peut être calculé sans persister le snapshot.

Séquence efficace :

```text
fingerprint candidate
  ↓
if identical to published:
   no-op
else:
   diff
   guard
   snapshot/version only if accepted
```

Cela évite de persister des versions rejetées inutilement.

---

# 242. Candidate snapshots rejetés

Un run rejeté peut toujours conserver ses artefacts de run et `diff.json`.

Mais il n'a pas besoin d'entrer dans le registre cross-run des versions publiables.

V0.4 peut choisir :

```text
version registry = versions validées/promouvables
```

et non tous les candidats invalides.

---

# 243. Recommandation de lifecycle version

```text
candidate Dataset
   ↓
fingerprint
   ↓
diff/guard
   ↓
if accepted:
   create/reuse DatasetVersion
   ↓
optional publish
```

C'est plus propre que de versionner systématiquement chaque output intermédiaire.

---

# 244. PublishedDataset et environnement

Un workspace correspond à un environnement opérationnel.

Donc :

```text
prod workspace published/current
staging workspace published/current
```

La V0.4 ne crée pas de champ `environment` dans chaque version si le workspace suffit.

---

# 245. Multi-workspace

Les versions d'un workspace ne sont pas automatiquement répliquées vers un autre.

Promotion staging → prod appartient à une stratégie de déploiement/target future ou à l'orchestrateur.

Pas de sync multi-environnement en V0.4.

---

# 246. CLI JSON

Toutes les nouvelles commandes d'inspection doivent supporter :

```text
--json
```

avec schémas déterministes.

Cela facilite automatisation externe sans transformer PyIngestKit en service web.

---

# 247. Exit codes

Principes :

```text
0 success
non-zero configuration/not-found/corruption/replay mismatch
```

Un diff qui contient des changements n'est pas une erreur en soi.

Le `DiffGuard` détermine éventuellement l'échec.

---

# 248. `pyingest diff` exit code

Si le diff s'exécute correctement :

```text
exit 0 même si added/removed/changed > 0
```

Sauf option future de policy gate explicite.

---

# 249. `pyingest replay` exit code

```text
0 → replay succeeded and verification passed / disabled
non-zero → execution failure / integrity failure / strict mismatch
```

---

# 250. Backward compatibility

La V0.4 stable doit préserver :

```text
Dataset API V0.3
CsvParser
JsonParser
NdjsonParser
ExcelParser
ParquetParser
DatasetContract V2
DatasetProfiler
ValidationResult
Quality reports
Runner existing semantics
MetadataStore official adapters
CLI V0.3 commands
six reference jobs
```

---

# 251. MetadataStore compatibility test

Créer dans les tests un fake custom store V0.3 implémentant uniquement l'ABC existant.

V0.4 Runner doit encore fonctionner avec lui pour un job sans features V0.4.

C'est un garde-fou important contre une rupture accidentelle.

---

# 252. Manifest compatibility

Les nouvelles clés sont additives.

Un consommateur V0.3 lisant les anciennes clés ne doit pas être cassé.

Éviter de renommer :

```text
reports
validations
artifacts
steps
```

---

# 253. Snapshot compatibility

Un snapshot V1 doit rester lisible pendant tout le cycle V0.x sauf faille critique.

La lecture future doit dispatcher sur :

```text
snapshot_version
```

---

# 254. Diff report compatibility

Même discipline :

```text
report_version
```

Les champs requis V1 ne doivent pas être supprimés en patch release.

---

# 255. Security checklist V0.4

Avant stable :

```text
[ ] no pickle
[ ] snapshot paths traversal-safe
[ ] version IDs validated
[ ] current pointer atomic
[ ] diff reports no full values by default
[ ] diff key previews redacted
[ ] replay never restores secrets
[ ] replay strict never falls back live
[ ] replay hash verified
[ ] snapshot hash verified on load
[ ] no source headers persisted newly
[ ] events contain summaries only
[ ] temp files not treated as versions
[ ] Bandit green
[ ] pip-audit green
```

---

# 256. Determinism checklist

```text
[ ] canonical_version frozen
[ ] dict order invariant
[ ] row order policy explicit
[ ] duplicate rows preserved
[ ] type-aware comparison
[ ] NaN stable
[ ] datetime serialization stable
[ ] Decimal exact
[ ] diff entry ordering stable
[ ] snapshot round-trip stable
[ ] replay expected fingerprint stable
```

---

# 257. Performance checklist

```text
[ ] keyed diff O(n+m)
[ ] no O(n*m) joins
[ ] max_entries enforced
[ ] no duplicate full row copies when unnecessary
[ ] fingerprint documented O(n log n) if order-insensitive
[ ] snapshot atomic
[ ] version dedup identical content
[ ] replay copies bytes once
```

---

# 258. Release gate

Conserver :

```bash
make release-check
```

Il doit couvrir :

```text
check
quality
security
build
wheel-smoke
```

---

# 259. CI matrix

V0.4 :

```text
Python 3.11 ✅
Python 3.12 ✅
Python 3.13 ✅
```

Au moins un job CI Python 3.12 exécute la verticale complète versioning/replay avec OpenPyXL et PyArrow installés pour conserver la non-régression V0.3.

---

# 260. Offline replay CI

Le test CI de replay HTTP doit explicitement bloquer le réseau :

```python
socket.socket.connect = fail
```

ou équivalent contrôlé.

Un replay qui passe uniquement parce que le réseau est disponible n'est pas une preuve suffisante.

---

# 261. Wheel-installed replay

Le replay E2E le plus important doit être exécuté depuis :

```text
framework wheel
+
demo pack wheel
```

pas seulement depuis un checkout editable.

---

# 262. Release artifacts stable

Minimum :

```text
pyingestkit-0.4.0-py3-none-any.whl
pyingestkit-0.4.0.tar.gz
pyingestkit_demo_jobs-0.4.0-py3-none-any.whl
pyingestkit_demo_jobs-0.4.0.tar.gz
SHA256SUMS-v0.4.0.txt
```

Le source ZIP de travail peut être livré séparément mais ne doit pas être confondu avec le source archive GitHub auto-generated.

---

# 263. Checksums

Le problème de cohérence checksum rencontré historiquement doit être évité.

La procédure stable doit :

1. construire les artefacts finaux une seule fois ;
2. calculer leurs SHA-256 ;
3. écrire `SHA256SUMS-v0.4.0.txt` ;
4. vérifier `shasum -c` ;
5. attacher exactement ces mêmes bytes à la GitHub Release ;
6. comparer les digests GitHub API aux checksums locaux.

---

# 264. Release qualification evidence

Créer :

```text
docs/reviews/v0.4.0-release-review.md
```

avec :

```text
commit SHA
tag object SHA
CI run IDs
Security run ID
unittest count
pytest count
Ruff
Mypy
Bandit
pip-audit
wheel smoke
replay network-blocked proof
checksums
```

---

# 265. V0.4 stable freeze

Après release :

```text
V0.4.0 Diff / Replay / Versioning → frozen
```

Les patches V0.4.x ne doivent contenir que :

- bugfix ;
- security ;
- docs ;
- packaging ;
- compatibility fixes.

Pas de nouveaux targets V0.5 dans V0.4.x.

---

# 266. Transition vers V0.5

La V0.4 prépare V0.5 en fournissant :

```text
DatasetVersion
PublishedDataset
DiffResult
snapshot/fingerprint
replay lineage
```

V0.5 pourra ajouter :

```text
PostgresTarget
bulk load
atomic target promotion
```

et associer un `DatasetVersion` à une publication externe transactionnelle.

---

# 267. Ce que V0.5 ne doit pas rouvrir

V0.5 ne devra pas redéfinir :

```text
Dataset fingerprint
snapshot format
diff semantics
replay lineage
PublishedDataset identity
```

sauf incompatibilité démontrée.

---

# 268. Relationship with orchestrators

Un orchestrateur externe pourra faire :

```text
schedule job
  ↓
run PyIngestKit
  ↓
inspect diff guard
  ↓
alert / approve
  ↓
publish
```

PyIngestKit ne doit pas créer lui-même un scheduler d'approbation.

---

# 269. Manual approval

Un workflow métier peut vouloir une approbation humaine lorsque le diff dépasse un seuil.

Le framework fournit :

```text
diff report
status
version candidate
```

L'orchestrateur/UI externe gère l'approbation.

Pas d'UI d'approbation en V0.4.

---

# 270. Example — postal codes

```python
policy = DiffPolicy(
    key_fields=("code_postal", "code_commune"),
    ignore_fields=("date_extraction",),
)

diff = DatasetDiffer(policy).compare(previous, candidate)
```

Rapport :

```text
added:   18
removed: 3
changed: 7
```

Un pack métier peut refuser la publication si :

```text
removed_ratio > 1%
```

---

# 271. Example — NAF

Clé :

```text
code_naf
```

Champs significatifs :

```text
libelle
niveau
parent_code
```

Le framework ne connaît pas la signification de NAF ; il applique seulement la policy fournie.

---

# 272. Example — company registry

Un dataset d'entreprises peut être sensible et volumineux.

V0.4 doit permettre :

```text
capture_values=False
max_entries=100
```

pour produire un rapport exploitable sans dumper les données.

---

# 273. Example — replay après bug parser

Scénario :

```text
run A acquis 100 MB de données
bug de parsing détecté le lendemain
source externe a déjà changé
```

Avec V0.4 :

```bash
pyingest replay <run-A> --allow-version-change
```

Le nouveau parser travaille sur **exactement les bytes du run A**.

C'est une capacité majeure pour l'audit et le débogage.

---

# 274. Example — validation de refactor

```text
job v1.3.0 → fingerprint X
refactor interne
job v1.4.0 → replay same RAW → fingerprint X
```

Conclusion :

```text
refactor did not alter logical output
```

La V0.4 transforme ce constat en preuve automatique.

---

# 275. Example — intentional migration

```text
job v1.4.0 → fingerprint X
job v2.0.0 → changed normalization → fingerprint Y
```

Replay avec `--allow-version-change` + diff :

```text
what exactly changed between X and Y?
```

Très utile pour les migrations de référentiels.

---

# 276. Future provenance strength

V0.4 ne capture pas encore l'environnement Python complet (`pip freeze`) dans chaque run.

Cela pourrait être utile à long terme mais risque de :

- grossir les manifests ;
- exposer des packages internes ;
- créer de la complexité.

Pour V0.4, capturer :

```text
framework version
job version
raw sha256
parameters
as_of
fingerprint
```

est suffisant.

---

# 277. Replay reproducibility levels

Proposition documentaire :

```text
LEVEL 0 — RAW available
LEVEL 1 — RAW + job id/version + params
LEVEL 2 — + as_of + framework version
LEVEL 3 — + expected Dataset fingerprint
```

La V0.4 vise Level 3 pour les nouveaux runs versionnés.

---

# 278. Replay result

Proposition :

```python
@dataclass(frozen=True, slots=True)
class ReplayResult:
    source_run_id: str
    replay_run_id: str
    source_job_version: str
    executed_job_version: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None
    matched: bool | None
```

---

# 279. Replay result ≠ RunResult

`ReplayResult` peut contenir/référencer le `RunResult`, mais il ne doit pas remplacer son rôle.

Le run reste l'unité runtime canonique.

Replay ajoute seulement la lineage et la vérification.

---

# 280. Version API and multiple Datasets per Step

Un Step peut théoriquement produire plusieurs Datasets.

V0.4 ne doit pas auto-versionner tous les Datasets nested outputs.

La création de version reste explicitement déclenchée avec un `dataset_id`.

Cela évite les ambiguïtés.

---

# 281. Diff observation and nested outputs

À l'inverse, si un Step produit explicitement un `DatasetDiff` nested dans un mapping/list, le Runner peut l'observer comme pour `ValidationResult`/`DatasetProfile`.

Cela est cohérent avec V0.3.

---

# 282. Multiple diffs per run

Si plusieurs diffs sont observés :

```text
reports/<step>/diff-1.json
reports/<step>/diff-2.json
```

ou structure équivalente déterministe.

Aucun overwrite du premier report.

La convention exacte doit être testée avant A2 freeze.

---

# 283. Multiple DatasetVersions per run

Un run peut produire plusieurs `dataset_id`.

La metadata doit donc utiliser :

```text
(run_id, dataset_id, version_id)
```

et non supposer une seule version par run.

---

# 284. Published current pointer per dataset

Il existe au maximum :

```text
1 current pointer per dataset_id per workspace
```

Le filesystem path matérialise cette contrainte naturellement.

---

# 285. Dataset version URI stability

Une version content-addressed ne doit pas être déplacée lorsque publiée/superseded.

`current.json` change ; le snapshot reste au même URI.

Cela rend les références historiques fiables.

---

# 286. Audit trail

Pour chaque publication, on doit pouvoir répondre :

```text
Quelle version ?
Quel run ?
Quel RAW ?
Quel job version ?
Quel diff ?
Quelle validation ?
Quand ?
```

C'est un critère de Definition of Done V0.4.

---

# 287. No hidden state

Éviter des caches process-memory indispensables au versioning/replay.

Après redémarrage :

```text
versions
published current
metadata
runs
```

doivent suffire à reconstruire l'état opérationnel.

---

# 288. Process isolation

Le replay et la CLI doivent fonctionner dans un nouveau processus après le run initial.

Tests obligatoires via `CliRunner`/subprocess selon le cas.

Ne pas dépendre d'objets Python conservés en mémoire.

---

# 289. CLI run prefix

Comme `status`, `replay` peut accepter un préfixe de run uniquement s'il est non ambigu.

Si plusieurs runs matchent :

```text
explicit ambiguity error
```

---

# 290. Version prefix

Même approche possible pour les longs `sha256-...`, mais uniquement si non ambigu.

Un préfixe de 8/12 chars peut être utile en CLI ; l'identité persistée reste complète.

---

# 291. JSON-safe key representation

Les clés composites peuvent contenir date/Decimal/etc.

Le diff report doit les sérialiser via le codec canonique sûr, pas via `str(tuple)` arbitraire.

---

# 292. Redaction key representation

Si un field name de clé ressemble à :

```text
token
password
secret
api_key
```

la sortie report doit redacter sa valeur.

Le fingerprint/diff in-memory utilisent toutefois la vraie valeur.

---

# 293. Diff equality semantics freeze

Avant A1 stable, figer précisément :

```text
missing vs None
type-aware equality
NaN
nested mappings
list order
tuple vs list
field order
row order policy
schema-added behavior
```

Ces choix deviennent difficiles à modifier ensuite sans changer les fingerprints.

---

# 294. Snapshot equality semantics

Le snapshot doit préserver :

```text
list ≠ tuple
int ≠ float
bool ≠ int
date ≠ datetime
bytes ≠ str
missing ≠ None
```

Sinon le replay depuis snapshot/diff historique devient ambigu.

---

# 295. Stable canonical test vectors

Créer un fichier de tests avec des vectors connus :

```text
input Dataset
expected canonical payload hash
```

Ces hashes constituent un contrat de non-régression du fingerprint.

---

# 296. Golden vectors caution

Les golden hashes sont appropriés ici car le fingerprint **est précisément une API de stabilité**.

Contrairement à un test UI, une variation de hash doit être revue consciemment.

---

# 297. Snapshot compression

V0.4 ne compresse pas par défaut les snapshots.

Ajouter gzip/zstd compliquerait :

- random inspection ;
- deps ;
- atomicity ;
- checksum semantics.

Une future option peut être ajoutée si les snapshots réels sont trop volumineux.

---

# 298. Snapshot extension

Nom recommandé :

```text
dataset.snapshot.json
```

Il indique clairement qu'il ne s'agit pas d'un JSON métier source.

---

# 299. Version metadata file

Nom :

```text
version.json
```

Ce fichier est petit, inspectable et contient la provenance de la version.

---

# 300. Published pointer file

Nom :

```text
current.json
```

Contenu minimal :

```json
{
  "pointer_version": "1",
  "dataset_id": "public.postal_codes",
  "version_id": "sha256-...",
  "published_at": "...",
  "published_from_run_id": "..."
}
```

---

# 301. Pointer verification

`get_published()` doit :

1. lire `current.json` ;
2. retrouver la version ;
3. vérifier que son snapshot existe ;
4. vérifier le fingerprint si nécessaire ;
5. retourner `PublishedDataset`.

Un pointer cassé est une erreur d'intégrité explicite.

---

# 302. AtomicPointer abstraction ?

Ne créer une abstraction `AtomicPointer` que si le code publication/registry la justifie réellement.

Sinon réutiliser `AtomicPublisher` et garder l'implémentation simple.

Éviter les abstractions spéculatives.

---

# 303. VersionStore locking

V0.4 n'ajoute pas de lock manager.

Documenter single-writer et prévoir un champ `expected_current_version_id` optionnel uniquement si une CAS simple peut être implémentée de manière fiable.

Sinon ne pas promettre une garantie incomplète.

---

# 304. Crash scenarios

Tester au minimum :

```text
snapshot write fails before current pointer
→ published old remains

pointer temp write fails
→ published old remains

metadata write fails after pointer
→ pointer remains canonical; metadata can be reconciled
```

La priorité est :

```text
ne jamais casser la dernière version publiée valide
```

---

# 305. Diff report before publication failure

Même si publication échoue, `diff.json` doit rester dans le run pour expliquer ce qui aurait changé.

---

# 306. Publication event ordering

Émettre :

```text
DATASET_PUBLISHED
```

uniquement après `current.json` réussi.

Jamais avant.

---

# 307. Replay event ordering

`REPLAY_COMPLETED` uniquement après fin du nouveau run et vérification éventuelle.

En cas d'échec, utiliser le lifecycle run normal + event de replay failure si vraiment utile, sans proliférer.

---

# 308. Diff status in run

Un diff n'est pas un nouveau statut global de run.

Éviter :

```text
DIFFING
```

sauf besoin réel.

Les steps/events suffisent.

---

# 309. Versioning status in run

Même logique : pas besoin d'ajouter `VERSIONING` au RunStatus.

La V0.1 a volontairement gardé des statuts globaux simples.

---

# 310. Replay run status

Un replay utilise les mêmes :

```text
RUNNING
SUCCESS
FAILED
```

La nature replay est une metadata, pas un nouveau RunStatus.

---

# 311. Framework version in manifest

V0.4 devrait ajouter additivement :

```text
framework_version
```

au manifest pour renforcer la reproductibilité.

Cela ne remplace pas `job_version`.

---

# 312. Python version

La Python version peut être utile dans `run_reproducibility`, mais n'est pas obligatoire pour A1.

Recommandation : l'ajouter en B2 si cela reste simple :

```text
python_version = 3.12.13
```

Cela aide à expliquer certains comportements de parsing/types.

---

# 313. Platform info

Ne pas stocker une énorme empreinte machine.

Un petit set peut suffire :

```text
python_version
platform_system
```

mais rester prudent sur la privacy/portabilité.

---

# 314. Dependency lock replay

V0.4 ne cherche pas à recréer automatiquement un venv historique exact.

C'est un problème de build/reproducible environments, pas de RAW replay.

La documentation doit le dire clairement.

---

# 315. Replay claim precise

PyIngestKit V0.4 garantit :

> **rejouer le pipeline courant sur les mêmes RAW bytes, avec lineage et comparaison de fingerprint lorsque les métadonnées nécessaires sont disponibles.**

Il ne garantit pas :

> recréer bit-for-bit l'environnement système entier du passé.

---

# 316. DatasetSnapshot vs RawArtifact

```text
RawArtifact
  = bytes source exacts

DatasetSnapshot
  = représentation interne du Dataset après parsing/normalisation
```

Les deux sont utiles et complémentaires.

---

# 317. Replay source from snapshot ?

Commande `replay` repart par défaut du RAW, pas du snapshot.

Pourquoi ?

Parce que le but est de retester parsing/normalisation/validation.

Un chargement snapshot est destiné au diff/versioning, pas au replay du pipeline complet.

---

# 318. Future partial replay

Un futur mode pourrait repartir d'un snapshot/stage intermédiaire.

Hors V0.4.

Ne pas introduire :

```text
replay --from-step
```

avant un besoin réel.

---

# 319. Replay multi-RAW

Un run peut avoir plusieurs RAW artifacts.

ReplayContext doit donc gérer un mapping/list, pas un seul artifact global.

La résolution doit être déterministe.

---

# 320. Replay ambiguous RAW

Si deux RAW historiques correspondent au même nom/source attendu :

```text
ReplayError: ambiguous raw artifact
```

Le framework ne choisit pas arbitrairement.

---

# 321. Source URI redaction

Les URLs historique restent celles déjà sanitisées par V0.2.

Replay ne doit pas reconstruire une URL avec les secrets originaux.

---

# 322. ETag / Last-Modified

Ces métadonnées peuvent être copiées comme provenance héritée du RAW original.

Le replay report doit préciser qu'elles proviennent de l'acquisition d'origine, pas d'un nouvel échange HTTP.

---

# 323. Retrieved time

Distinguer :

```text
origin_retrieved_at
replay_materialized_at
```

Le nouveau RawArtifact possède son `retrieved_at` de matérialisation dans le nouveau run ; la lineage conserve l'heure d'acquisition originale.

---

# 324. Replay and config files

Le run history conserve les paramètres runtime, pas nécessairement le fichier YAML complet original.

V0.4 ne doit pas prétendre reconstruire un YAML disparu.

La CLI replay utilise :

- job id/version ;
- parameters enregistrés ;
- overrides ;
- metadata reproducibility.

---

# 325. Replay of removed job

Si le plugin/job n'est plus installé :

```text
ReplayError(job_not_found)
```

La CLI doit expliquer comment réinstaller la version du job plutôt que masquer l'erreur.

---

# 326. Replay of version mismatch

Message utile :

```text
Source run used job 1.3.0; installed job is 1.4.0.
Use --allow-version-change to replay intentionally with the installed version.
```

---

# 327. Version metadata source artifacts

Si un Dataset combine plusieurs RAW artifacts, un seul `source_artifact_id` est insuffisant.

V0.4 doit éviter de figer un modèle mono-source trop rigide.

Recommandation :

```text
source_artifact_ids: tuple[str, ...]
source_raw_sha256s: tuple[str, ...]
```

ou une table de relation version↔artifacts.

---

# 328. Dataset source linkage V0.3 limitation

`Dataset.source_artifact_id` est actuellement singulier.

Ne pas casser ce champ en V0.4.

Pour les versions multi-source, la versioning API peut accepter explicitement une collection de source artifacts en plus du lien Dataset existant.

---

# 329. Version artifacts relation table

Option robuste :

```text
dataset_version_artifacts
-------------------------
dataset_id
version_id
artifact_id
sha256
position
```

Cela prépare les jobs multi-sources sans modifier `Dataset`.

---

# 330. Scope initial single-source

Pour A1/B1, le reference job peut rester single-source.

Mais le schema ne doit pas rendre multi-source impossible.

---

# 331. Diff against arbitrary version

Le moteur de diff Python compare deux Datasets quelconques.

Le store/CLI peut charger :

```text
version N-1
version N-4
published
candidate
```

La comparaison ne dépend pas forcément du "previous" chronologique.

---

# 332. Version chronology

Content-addressed IDs ne contiennent pas d'ordre temporel.

Le `created_at` et la relation run fournissent la chronologie.

Ne pas essayer d'encoder un numéro séquentiel dans le fingerprint.

---

# 333. Human-friendly display

CLI peut afficher :

```text
sha256-7f81b0d6a18b
```

comme préfixe court, mais JSON/API renvoie l'ID complet.

---

# 334. External version labels

Un champ metadata optionnel :

```text
external_version
```

peut capturer :

```text
"NAF 2025"
"PCG 2026"
"2026-09-04"
```

sans influencer le fingerprint.

À ajouter seulement si le reference job en démontre le besoin.

---

# 335. Diff report and external version

Le rapport peut afficher le label s'il existe, mais l'identité technique reste `version_id`.

---

# 336. Quality report cross-links

Un diff report peut référencer :

```text
candidate validation report
candidate profile report
```

uniquement via paths/IDs, sans duplication.

---

# 337. Version metadata cross-links

`version.json` peut lister :

```text
reports:
  validation
  profile
  diff
```

Ce sont des pointers de provenance du run de création.

---

# 338. Historical reports retention

Si les run directories sont supprimés manuellement, les pointers report de `version.json` peuvent devenir cassés.

V0.4 ne garantit pas leur retention éternelle.

Les preuves minimales durables de version sont :

```text
snapshot
version.json
fingerprint
run id lineage
```

---

# 339. Future immutable report copies

Copier des quality/diff reports dans le dossier de version pourrait renforcer l'audit, mais dupliquerait des données.

À décider après pilotes ; pas nécessaire pour B1.

---

# 340. Version store abstraction and metadata store

Ne pas coupler `FilesystemDatasetVersionStore` directement à SQLAlchemy.

Le version store peut recevoir une capability metadata optionnelle.

Cela permet :

```text
filesystem versions + MemoryMetadataStore
filesystem versions + SQLite
filesystem versions + Postgres metadata
```

---

# 341. Failure without metadata capability

Si le version store peut persister son `version.json` mais le metadata store n'a pas la capability V0.4 :

- l'opération filesystem peut réussir ;
- un warning opérationnel peut signaler la metadata non indexée ;
- ne pas casser les stores custom V0.3.

Le comportement exact doit être explicite.

---

# 342. Recommended metadata fallback

Pour la stable, préférer :

```text
official stores → full queryable metadata
custom old store → filesystem truth + events only
```

pas une exception obligatoire.

---

# 343. Release gate custom-store compatibility

Ajouter un contract test qui exécute :

```text
V0.3 job + legacy custom MetadataStore
```

sous V0.4.

---

# 344. Replay metadata fallback

Replay peut fonctionner via filesystem artifacts + base MetadataStore run/artifact queries.

Les détails enrichis de lineage dans `ReplayMetadataCapability` sont optionnels pour les custom stores.

---

# 345. Built-in store completeness

En revanche les trois built-ins officiels :

```text
MemoryMetadataStore
SQLiteMetadataStore
PostgresMetadataStore
```

doivent supporter les features V0.4 complètes ou clairement documenter une différence.

---

# 346. MemoryMetadataStore

Pour tests, il doit pouvoir conserver :

```text
diffs
versions
published pointers metadata
replay lineage
```

sans filesystem persistence de metadata.

Le version snapshot lui-même reste dans FilesystemDatasetVersionStore dans les tests E2E.

---

# 347. SQLAlchemy schema

Les nouvelles tables restent dans le module canonique `_schema.py` afin de conserver une seule définition pour SQLite/Postgres.

Pas de duplication Peewee/SQLAlchemy.

---

# 348. Alembic posture

V0.4 peut encore éviter Alembic si :

```text
all schema changes are additive new tables/indexes
```

Si l'implémentation découvre le besoin de modifier une colonne existante, reconsidérer explicitement la décision avant de contourner le problème.

---

# 349. Additive indexes

Indexes utiles :

```text
dataset_versions(dataset_id, created_at DESC)
dataset_version_runs(run_id)
dataset_diffs(run_id)
dataset_diffs(dataset_id, created_at DESC)
replay_runs(source_run_id)
```

Ne pas sur-indexer le MVP.

---

# 350. SQL portability

Utiliser SQLAlchemy Core comme Foundation.

Pas de SQL SQLite spécifique dans la logique commune sauf adapter.

---

# 351. Publication metadata transaction

Pour l'index SQL `published_datasets`, utiliser une transaction/upsert adaptée au dialecte via SQLAlchemy Core.

La source de vérité filesystem reste indépendante.

---

# 352. No DB target confusion

Le fait d'utiliser PostgreSQL comme MetadataStore ne signifie pas que le Dataset est chargé dans PostgreSQL.

V0.5 ajoutera `PostgresTarget` séparément.

---

# 353. Runtime run result

Ne pas gonfler `RunResult` avec tous les diffs/versions.

Le manifest/metadata/status sont les surfaces d'inspection.

Ajouter seulement des champs si le besoin API est démontré.

---

# 354. StepResult metrics

Un step de diff peut exposer :

```text
added_count
removed_count
changed_count
```

via `StepResult.metrics` ou ses propres metrics context.

Cela reste optionnel.

---

# 355. Diff policy serialization

Le `diff.json` doit sérialiser la policy qui a produit le résultat.

Cela aide l'audit : un même couple de datasets peut produire des diffs différents selon les champs ignorés.

---

# 356. Policy fingerprint future

On peut calculer un petit fingerprint de policy si utile, mais ce n'est pas requis pour A1.

Le JSON explicite suffit.

---

# 357. Replay policy

De même, replay doit enregistrer :

```text
strict_live_fallback=False
allow_version_change
verification_mode
parameter_overrides keys
```

Ne jamais enregistrer la valeur d'un override secret.

---

# 358. Parameter override audit

La metadata peut enregistrer les noms des paramètres overridden :

```text
overridden_parameters = ["api_token"]
```

mais appliquer redaction et ne pas exposer les valeurs sensibles.

---

# 359. Replay expected fingerprint source

Ordre de résolution recommandé :

```text
1. DatasetVersion liée au source run
2. manifest V0.4 dataset_versions
3. explicit --expected-fingerprint
4. None → replay sans vérification exacte
```

---

# 360. Run to version relation

Lorsqu'un run crée/réutilise une version, écrire la relation `dataset_version_runs` même si la version existait déjà.

Cela permet de retrouver tous les runs produisant le même output.

---

# 361. Replay and version relation

Un replay strict qui reproduit le même fingerprint doit aussi pouvoir enregistrer :

```text
replay run → existing DatasetVersion
```

sans créer un nouveau snapshot.

---

# 362. Replay no publication

Même si le replay reproduit une version existante, il ne touche pas `current.json` par défaut.

C'est une règle de sécurité importante.

---

# 363. Replay explicit publish future

Une option :

```text
--publish
```

peut être envisagée plus tard, mais n'est pas nécessaire pour B2.

L'utilisateur peut exécuter une publication séparée si besoin.

---

# 364. V0.4 product statement

À la fin de V0.4, PyIngestKit pourra dire :

> **PyIngestKit sait non seulement acquérir, parser et qualifier un dataset, mais aussi détecter ses changements, lui attribuer une identité de contenu, conserver ses versions publiées et rejouer un traitement depuis les RAW capturés.**

---

# 365. Lifecycle V0.4 complet

```text
DISCOVER
    ↓
FETCH / REPLAY RAW
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
PROFILE
    ↓
FINGERPRINT
    ↓
DIFF
    ↓
QUALITY / DIFF GUARD
    ↓
VERSION SNAPSHOT
    ↓
ATOMIC PUBLISH
    ↓
MANIFEST / METADATA / EVENTS
```

Tous les jobs ne sont pas obligés d'utiliser chaque étape.

---

# 366. Roadmap globale après V0.4

```text
V0.1  Foundation                    ✅
V0.2  Acquisition                   ✅
V0.3  Quality & Formats             ✅ baseline
V0.4  Diff / Replay / Versioning    ← ce plan
V0.5  Persistence Targets
V0.6  Object Storage if justified
V1.0  Stable Framework Contract
```

---

# 367. Readiness pour V0.5

V0.5 pourra utiliser :

```text
PublishedDataset.version_id
```

comme identité de la donnée à charger dans une target.

Cela rend possibles des invariants tels que :

```text
Target X currently contains DatasetVersion Y
```

sans réinventer le versioning dans chaque target.

---

# 368. V1 readiness contribution

V0.4 est critique pour V1 car elle ferme trois promesses de la vision initiale :

```text
traceability of changes
reproducibility
canonical publication history
```

Sans ces capacités, PyIngestKit resterait surtout un bon fetch/parse framework.

---

# 369. Décision de lancement recommandée

Une fois V0.3.0 officiellement taguée/released :

```text
1. create feat/v0.4-diff-replay-versioning
2. create ADR-034 canonical fingerprint semantics
3. implement V0.4.0-a1 only
4. freeze diff equality semantics before runtime integration
5. deliver a1 ZIP
6. continue sequentially a2 → b1 → b2 → rc1 → stable
```

---

# 370. Premier scope d'implémentation à ne pas dépasser

Le premier cycle doit rester strictement :

```text
V0.4.0-a1
DATASET FINGERPRINTS + DIFF ENGINE
```

Fichiers probables :

```text
src/pyingestkit/diff/__init__.py
src/pyingestkit/diff/models.py
src/pyingestkit/diff/policy.py
src/pyingestkit/diff/engine.py

src/pyingestkit/versioning/canonical.py
src/pyingestkit/versioning/fingerprint.py

src/pyingestkit/core/exceptions.py

tests/unit/diff/test_dataset_differ.py
tests/unit/versioning/test_dataset_fingerprint.py
tests/contract/test_diff_public_api.py

docs/adr/ADR-034-*.md
docs/adr/ADR-035-*.md
docs/guides/dataset-diff.md
```

Pas de persistence/version registry/replay dans A1.

---

# 371. Acceptance criteria A1 détaillés

Avant livraison A1 :

```text
[ ] canonical value semantics frozen
[ ] deterministic hash vectors committed
[ ] same logical Dataset → same fingerprint
[ ] row reorder behavior tested
[ ] schema affects fingerprint
[ ] typed values distinct
[ ] keyed diff exact
[ ] composite keys exact
[ ] duplicate keys rejected
[ ] keyless diff multiset exact
[ ] schema diff exact
[ ] missing vs None exact
[ ] entries ordering deterministic
[ ] max_entries deterministic
[ ] no Dataset mutation
[ ] no DataFrame dependency
[ ] no new mandatory dependency
[ ] V0.3 API contract green
[ ] Ruff green
[ ] Mypy green
[ ] Bandit green
[ ] pip-audit green
[ ] build green
[ ] V0.3 wheel-smoke non-regressed
```

---

# 372. Acceptance criteria A2 détaillés

```text
[ ] diff report_version=1
[ ] JSON report safe
[ ] values omitted by default
[ ] manifest ref additive
[ ] Runner observes DatasetDiff
[ ] multiple diffs do not overwrite
[ ] DIFF events deterministic
[ ] official metadata stores query diffs
[ ] legacy custom MetadataStore remains valid
[ ] status human/json show reports
[ ] release gates green
```

---

# 373. Acceptance criteria B1 détaillés

```text
[ ] snapshot_version=1
[ ] round-trip all V0.3 parser-native types
[ ] no pickle
[ ] no repr fallback
[ ] corruption detected
[ ] version_id content-addressed
[ ] identical content deduplicated
[ ] version history immutable
[ ] current pointer atomic
[ ] first publish works
[ ] second publish works
[ ] identical publish no-op
[ ] failed publish leaves old current intact
[ ] versions/published CLI human/json
[ ] additive metadata schema
[ ] release gates green
```

---

# 374. Acceptance criteria B2 détaillés

```text
[ ] replay strict default
[ ] no live fallback
[ ] HTTP replay no network
[ ] LocalSource replay no source read
[ ] new RAW sha equals origin
[ ] lineage recorded
[ ] same-version verification works
[ ] version mismatch blocked by default
[ ] --allow-version-change works
[ ] --no-verify works
[ ] secrets never reconstructed
[ ] replay does not republish
[ ] pre-V0.4 best-effort behavior documented
[ ] release gates green
```

---

# 375. Acceptance criteria RC1 détaillés

```text
[ ] seven demo jobs discoverable
[ ] all six V0.3 demos green
[ ] revision 1 creates/publishes V1
[ ] revision 2 diffs V1 correctly
[ ] diff report created
[ ] V2 created/published
[ ] versions CLI sees V1/V2
[ ] published CLI points to V2
[ ] replay revision 2 from RAW with network blocked
[ ] replay fingerprint == V2
[ ] metadata lineage complete
[ ] Python 3.11/3.12/3.13 green
[ ] security green
[ ] wheel smoke green
```

---

# 376. Acceptance criteria stable détaillés

```text
[ ] RC semantics unchanged
[ ] package version 0.4.0
[ ] demo pack version 0.4.0
[ ] README stable
[ ] CHANGELOG complete
[ ] ADR index complete
[ ] docs index complete
[ ] release-validation guide complete
[ ] make release-check exit 0
[ ] wheel/sdist clean
[ ] checksums verified against exact release assets
[ ] PR merged
[ ] tag v0.4.0 points to merge commit
[ ] GitHub Release published
[ ] release assets verified
```

---

# 377. Final architecture signature

```text
                     ┌──────────────────────┐
                     │   External Source    │
                     └──────────┬───────────┘
                                │
                         FETCH or REPLAY
                                │
                                ▼
                     ┌──────────────────────┐
                     │     RawArtifact      │
                     │ SHA-256 + provenance│
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │        Parser        │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │       Dataset        │
                     └──────┬───────┬───────┘
                            │       │
               ┌────────────┘       └─────────────┐
               ▼                                  ▼
     Validation / Profiling               Fingerprint
               │                                  │
               ▼                                  ▼
       Quality Reports                     Candidate identity
                                                  │
                                                  ▼
                                    ┌────────────────────────┐
                                    │    PublishedDataset    │
                                    │ current immutable ver. │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                           DatasetDiffer
                                                │
                                                ▼
                                            DatasetDiff
                                                │
                                       ┌────────┴────────┐
                                       ▼                 ▼
                                   diff.json         Diff Guard
                                                         │
                                                         ▼
                                                DatasetVersionStore
                                                         │
                                      ┌──────────────────┴───────────────┐
                                      ▼                                  ▼
                              immutable version                    atomic current
                                  snapshot                           pointer
                                      │                                  │
                                      └──────────────────┬───────────────┘
                                                         ▼
                                                  PublishedDataset
```

---

# 378. Principe à retenir

La V0.4 doit rendre vrai l'invariant suivant :

> **À partir d'un run publié, PyIngestKit doit pouvoir dire exactement quelle version logique du dataset a été produite, quelles différences la séparent de la version précédente, quels RAW l'ont générée, et rejouer ces RAW dans un nouveau run sans recontacter la source.**

C'est le cœur de **Diff / Replay / Versioning**.

---

# 379. Conclusion

V0.1 a donné à PyIngestKit un runtime fiable.  
V0.2 a sécurisé l'acquisition et le RAW.  
V0.3 a structuré la qualité et les formats.  
V0.4 doit maintenant apporter la **mémoire opérationnelle du dataset**.

La cible n'est pas de reproduire Git, DVC ou un lakehouse transactionnel. La cible est beaucoup plus précise :

```text
same RAW
  ↓
replayable processing
  ↓
Dataset fingerprint
  ↓
explicit diff
  ↓
immutable version
  ↓
atomic published pointer
  ↓
auditable lineage
```

Une fois ce socle stabilisé, PyIngestKit sera prêt à aborder V0.5 — **Persistence Targets** — avec une identité de données et une provenance suffisamment fortes pour charger des cibles externes sans perdre l'historique logique de ce qui a été publié.
