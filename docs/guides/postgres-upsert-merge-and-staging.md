# Guide Pratique : Ingestion Incrémentale PostgreSQL (UPSERT, MERGE & Staging Transactionnel)

Ce guide détaille l'utilisation avancée de l'adaptateur cible `PostgresTargetV2` pour synchroniser des jeux de données de manière incrémentale, sans doublons et avec un débit d'ingestion maximal grâce au **Staging Table Pattern**.

---

## 1. Vue d'Ensemble & Architecture du Staging

La commande native PostgreSQL `COPY ... FROM STDIN` offre les performances d'insertion les plus élevées du marché (50x à 100x plus rapide qu'un `INSERT` par lots), mais ne supporte pas directement la clause `ON CONFLICT DO UPDATE`.

Pour concilier vitesse extrême et réconciliation sans doublons, PyIngestKit applique le **Staging Table Pattern** au sein d'une transaction unique :

```mermaid
flowchart TD
    A["TargetLoadRequestV2<br/>mode=UPSERT / MERGE"] --> B["PostgresTargetV2.load()"]
    B --> C["CREATE TEMP TABLE _stg_xxx<br/>(LIKE target INCLUDING DEFAULTS)<br/>ON COMMIT DROP"]
    C --> D["Streaming COPY dans _stg_xxx<br/>(Débit maximal)"]
    D --> E["Réconciliation Atomique SQL<br/>ON CONFLICT DO UPDATE ou MERGE"]
    E --> F["Enregistrement Traçabilité<br/>_pyingest_target_loads"]
    F --> G["COMMIT Unique Transactionnel"]
    D -. Erreur .-> H["ROLLBACK Automatique<br/>(Table temporaire purgée, cible intacte)"]
```

```text
┌────────────────────────────────────────────────────────┐
│ TargetLoadRequestV2 (mode = UPSERT ou MERGE)           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ PostgresTargetV2.load()                                │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ CREATE TEMP TABLE _stg_xxx                             │
│ (LIKE destination INCLUDING DEFAULTS) ON COMMIT DROP   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Streaming COPY vers _stg_xxx (Protocole natif)         │
└─────────────┬────────────────────────────┬─────────────┘
              │ (Succès)                   │ (En cas d'échec)
              ▼                            ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│ Réconciliation SQL Atomique      │ │ ROLLBACK Automatique             │
│ INSERT ... ON CONFLICT DO UPDATE │ │ Table cible strictement intacte, │
│ ou MERGE INTO target             │ │ Table temporaire purgée          │
└─────────────┬────────────────────┘ └──────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────┐
│ Enregistrement Traçabilité       │
│ Table _pyingest_target_loads     │
└─────────────┬────────────────────┘
              │
              ▼
┌──────────────────────────────────┐
│ COMMIT Unique Transactionnel     │
└──────────────────────────────────┘
```

---

## 2. Exemple d'Ingestion en Mode `UPSERT`

Le mode `TargetLoadModeV2.UPSERT` permet d'insérer de nouvelles lignes tout en mettant à jour les lignes existantes en cas de conflit sur une ou plusieurs clés d'unicité (`key_columns`).

### Configuration de la Requête de Chargement

```python
from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.domain.decoding import DecodedRecord, DecodedRepresentation
from pyingestkit.domain.datasets import DatasetVersionReference, dataset_content_fingerprint
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.targets import TargetLoadModeV2, TargetLoadRequestV2

# 1. Préparation des données décodées
representation = DecodedRepresentation(
    records=(
        DecodedRecord(fields=(("user_id", "usr_001"), ("email", "alice@example.com"), ("status", "active"), ("score", 120))),
        DecodedRecord(fields=(("user_id", "usr_002"), ("email", "bob@example.com"), ("status", "verified"), ("score", 85))),
    )
)

# 2. Construction de la requête de chargement
run_id = IngestionRunId.new()
request = TargetLoadRequestV2(
    target_id="dw.postgres.primary",
    ingestion_run_id=run_id,
    correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    dataset_version=DatasetVersionReference(
        dataset_id="identity.users",
        version_id=dataset_content_fingerprint(representation),
    ),
    representation=representation,
    table="users",
    schema="public",
    mode=TargetLoadModeV2.UPSERT,
    key_columns=("user_id",),               # Clé de déduplication (conflit)
    update_columns=("status", "score"),     # Seules ces colonnes seront écrasées
    idempotent=True,                        # Ne recharge pas si déjà matérialisé
)

# 3. Exécution atomique
target = PostgresTargetV2(
    target_id="dw.postgres.primary",
    dsn="postgresql://user:pass@localhost:5432/production_db",
)
result = target.load(request)

if result.status.value == "succeeded":
    print(f"Chargement réussi : {result.rows_loaded} lignes réconciliées.")
```

### Comportement de `update_columns`
- **Explicite (`update_columns=("status", "score")`)** : Seules les colonnes indiquées sont modifiées lors d'un conflit. Les autres colonnes (ex: `email`) restent strictement inchangées pour les lignes existantes.
- **Par Défaut (`update_columns=()`)** : Toutes les colonnes de données (hors `key_columns`) sont automatiquement mises à jour (`EXCLUDED.col`).

---

## 3. Exemple d'Ingestion en Mode `MERGE` (Clés Composites)

Le mode `TargetLoadModeV2.MERGE` exploite l'instruction SQL standard `MERGE INTO` (disponible nativement sous PostgreSQL 15+ ou via un repli CTE automatique sous les versions antérieures) :

```python
request = TargetLoadRequestV2(
    target_id="dw.postgres.primary",
    ingestion_run_id=run_id,
    correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    dataset_version=version_ref,
    representation=stock_representation,
    table="warehouse_inventory",
    schema="inventory",
    mode=TargetLoadModeV2.MERGE,
    key_columns=("warehouse_code", "sku"),  # Clé composite
)
```

---

## 4. Traçabilité Technique & Contrôle d'Idempotence

Chaque chargement réussi est automatiquement consigné dans la table technique `_pyingest_target_loads` :

```sql
SELECT load_id, target_id, destination, dataset_version_id, mode, rows_loaded, completed_at
FROM public._pyingest_target_loads
ORDER BY completed_at DESC
LIMIT 5;
```

### Saut d'Idempotence (`idempotent=True`)
Lorsque `idempotent=True` est spécifié dans `TargetLoadRequestV2` :
1. L'adaptateur vérifie si un chargement avec statut `succeeded` existe déjà pour le tuple `(target_id, destination, dataset_version_id, mode)`.
2. Si trouvé, le chargement est **immédiatement sauté**, sans émettre de flux `COPY` ni modifier la table cible.
3. Le résultat renvoie un statut `SUCCEEDED` accompagné d'un diagnostic `target.postgres.skipped_idempotent`.

---

## 5. Recommandations de Performance

1. **Index d'Unicité :** Pour garantir la vitesse maximale de réconciliation lors d'un `UPSERT`, assurez-vous que `key_columns` correspond exactement à la clé primaire de la table ou à un index unique :
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS ux_users_user_id ON public.users (user_id);
   ```
2. **Maintenance des Tables Temporaires :** Les tables de staging utilisent `ON COMMIT DROP`, ce qui évite toute fragmentation de l'espace disque et dispense d'un appel ultérieur à `VACUUM`.
