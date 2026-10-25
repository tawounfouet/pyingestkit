# Analyse Technique & Architecture : Sémantique Cible PostgreSQL Avancée (UPSERT, MERGE & Staging Transactionnel) — LOT-36

- **Date :** 2026-10-25
- **Auteur :** Antigravity / Pair Programming
- **Item Backlog :** [`docs/build/backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md`](../build/backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../roadmap/post-2.0-scope-review.md) (Section 3.3)
- **LOT Cible :** LOT-36 (v2.2.0)
- **Références amont :**
  - Note de cadrage préalable : [`docs/analyses/cadrage/2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md`](./cadrage/2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md)
  - [`docs/architecture/v2-lot14-postgres-target.md`](../architecture/v2-lot14-postgres-target.md)
  - [`docs/adr/ADR-044-postgres-copy-primary-bulk-load-path.md`](../adr/ADR-044-postgres-copy-primary-bulk-load-path.md)
  - [`docs/adr/ADR-046-postgres-load-mode-transaction-semantics.md`](../adr/ADR-046-postgres-load-mode-transaction-semantics.md)
  - [`docs/adr/ADR-047-target-load-idempotency-history-driven.md`](../adr/ADR-047-target-load-idempotency-history-driven.md)

---

## 1. Contexte & Problématique Métier

Dans les architectures de données modernes (ELT, Lakehouse, réplication CDC, Data Warehouses PostgreSQL), les flux d'ingestion en production ne se limitent que rarement à des ajouts bruts continus (`APPEND`) ou des écrasements complets (`TRUNCATE_LOAD` / `REPLACE`).

Les pipelines industriels nécessitent très majoritairement une **synchronisation incrémentale par clé** :
- **Commandes & Achats :** Une commande ingérée avec le statut `"PENDING"` est ultérieurement réémise avec le statut `"SHIPPED"`.
- **Référentiels Clients (Customer 360) :** Les attributs d'un client (adresse, coordonnées) sont mis à jour sans dupliquer l'enregistrement principal.
- **Transactions Financières & Facturation :** Garantie d'absence absolue de doublons en cas de re-jeu réseau ou orchestration idempotente.

Dans l'état actuel de PyIngestKit V2 (introduit au LOT-14) :
1. `PostgresTargetV2` ne supporte que trois modes primitifs : `APPEND`, `TRUNCATE_LOAD`, et `REPLACE`.
2. **Le paradoxe PostgreSQL de `COPY` :** La commande PostgreSQL native `COPY ... FROM STDIN` est le vecteur d'ingestion de masse le plus performant du marché (50x à 100x plus rapide qu'un `INSERT` par lots), mais **le moteur PostgreSQL ne permet pas de clause `ON CONFLICT DO UPDATE` directement sur un flux `COPY`**.
3. **Risque de corruption lors de chargements destructifs ou partiels :** Si une transaction de chargement échoue en cours d'insertion, les tables cibles peuvent être laissées dans un état corrompu ou partiellement vidé si les opérations ne sont pas strictement isolées.
4. **Manque de traçabilité d'idempotence au niveau cible :** Bien que les Dataset Versions V2 soient immuables et adressées par contenu (empreinte SHA-256), `PostgresTargetV2` n'enregistre pas l'historique de ses matérialisations dans une table technique, rendant impossible la détection des chargements déjà effectués.

---

## 2. Benchmark & État de l'Art

| Mécanisme de Chargement | Performance (100k lignes) | Support des Conflits / Déduplication | Isolation & Atomicité | Robustesse aux Pannes |
| :--- | :--- | :--- | :--- | :--- |
| **A. `INSERT INTO ... VALUES (...)` par lots** | Très Lente (~35 à 60s) | Natif (`ON CONFLICT DO UPDATE`) | Moyenne (verrous par batch) | Faible si batch partiel |
| **B. Direct `COPY ... FROM STDIN` (Actuel)** | Ultra-Rapide (~0.3 à 0.8s) | **Aucun** (échec sur violation de clé) | Haute (1 transaction) | Haute (rollback automatique) |
| **C. Staging Table Pattern + `COPY` + SQL reconciliation (Cible LOT-36)** | **Excellente (~0.9 à 1.5s)** | **Total (`UPSERT` & `MERGE` déclaratif)** | **Absolue (`TEMP TABLE ... ON COMMIT DROP`)** | **Maximale (zéro pollution si échec)** |

### Le "Staging Table Pattern" : Standard de l'Industrie
Adopté par les frameworks d'ingestion et de transformation de référence (dbt, Snowflake loader, BigQuery load jobs, AWS Redshift copy), ce pattern décompose l'opération en 4 phases au sein d'une **unique transaction atomique** :
1. `CREATE TEMP TABLE _stg_<uuid> (LIKE <target_table> INCLUDING DEFAULTS) ON COMMIT DROP;`
2. `COPY _stg_<uuid> (...) FROM STDIN;` (débit maximal)
3. Exécution d'une instruction SQL ensembliste :
   - Pour `UPSERT` : `INSERT INTO <target_table> SELECT * FROM _stg_<uuid> ON CONFLICT (<keys>) DO UPDATE SET ...`
   - Pour `MERGE` : `MERGE INTO <target_table> USING _stg_<uuid> ...` (PostgreSQL 15+) ou CTE d'insertion/mise à jour (PostgreSQL 13/14).
4. `COMMIT` global : la table temporaire est automatiquement détruite par PostgreSQL sans coût de garbage collection.

---

## 3. Analyse des Options Architecturales

### Option 1 : Déporter l'UPSERT dans la couche applicative (Python)
- Interroger la base pour charger les clés existantes en mémoire, filtrer les doublons en Python, puis émettre des `INSERT` et `UPDATE` distincts.
- *Rejet :* Consommation mémoire prohibitive sur les gros volumes, exposition à des conditions de concurrence (*race conditions*) entre plusieurs workers, et effondrement des performances.

### Option 2 : Écriture directe via `INSERT ... ON CONFLICT` en lots de 1 000 lignes
- *Rejet :* Abandonner le protocole `COPY` dégraderait les performances d'ingestion d'un facteur 50, rompant avec la promesse de performance de PyIngestKit.

### Option 3 (Retenue) : Staging Table Transactionnelle + Réconciliation SQL + Traçabilité Cible
- Conserve l'usage exclusif de `COPY` pour le transfert des octets.
- Déclare formellement les colonnes de clés de conflit (`key_columns`) et les colonnes de mise à jour (`update_columns`) dans `TargetLoadRequestV2`.
- Enregistre chaque matérialisation réussie dans la table technique `_pyingest_target_loads`.
- Supporte le contrôle d'idempotence (`idempotent: bool = False`) pour éviter les ré-injections redondantes d'un même `dataset_version_id`.

---

## 4. Spécification Détaillée des Nouveaux Contrats

### A. Extension du Domaine Cible (`src/pyingestkit/domain/targets/models.py`)

```python
class TargetLoadModeV2(StrEnum):
    APPEND = "append"
    TRUNCATE_LOAD = "truncate_load"
    REPLACE = "replace"
    UPSERT = "upsert"      # Nouveau (LOT-36)
    MERGE = "merge"        # Nouveau (LOT-36)

@dataclass(frozen=True, slots=True)
class TargetLoadRequestV2:
    target_id: str
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    dataset_version: DatasetVersionReference
    representation: DecodedRepresentation
    table: str
    schema: str | None = "public"
    mode: TargetLoadModeV2 = TargetLoadModeV2.APPEND
    expected_row_count: int | None = None
    columns: tuple[str, ...] = ()
    key_columns: tuple[str, ...] = ()       # Clés d'unicité obligatoires pour UPSERT/MERGE
    update_columns: tuple[str, ...] = ()    # Colonnes à modifier (défaut: toutes hors clés)
    idempotent: bool = False                # Si True, saute l'exécution si déjà matérialisé
```

### B. Table Technique d'Idempotence & Traçabilité (`_pyingest_target_loads`)

Schéma de la table créée automatiquement dans le schéma de la cible (ou schéma public) :

```sql
CREATE TABLE IF NOT EXISTS public._pyingest_target_loads (
    load_id VARCHAR(36) PRIMARY KEY,
    target_id VARCHAR(128) NOT NULL,
    destination VARCHAR(256) NOT NULL,
    dataset_id VARCHAR(128) NOT NULL,
    dataset_version_id VARCHAR(128) NOT NULL,
    ingestion_run_id VARCHAR(36) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    rows_loaded INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pyingest_target_loads_dedup
ON public._pyingest_target_loads (target_id, destination, dataset_version_id, mode);
```

### C. Algorithme de Chargement Staging & Réconciliation (`PostgresTargetV2`)

```text
PostgresTargetV2.load(request):
  1. Si request.idempotent == True:
       Vérifier si un enregistrement SUCCEEDED existe dans _pyingest_target_loads
       pour (target_id, destination, dataset_version_id, mode).
       Si oui: retourner TargetLoadResultV2 avec diagnostic 'target.postgres.skipped_idempotent'.
  2. Ouvrir connection transactionnelle: with engine.begin() as connection:
       a. Valider table et schéma via PostgresSchemaMapperV2.
       b. Si mode in (APPEND, TRUNCATE_LOAD, REPLACE):
            Exécuter chemin direct (préparation + COPY direct) [invariable].
       c. Si mode == UPSERT:
            - Valider que request.key_columns est non-vide.
            - Valider que request.key_columns sont des colonnes valides de la table.
            - Créer table temporaire:
                CREATE TEMP TABLE _stg_xxx (LIKE <destination> INCLUDING DEFAULTS) ON COMMIT DROP;
            - COPY dans _stg_xxx depuis request.representation.records.
            - Construire et exécuter:
                INSERT INTO <destination> (<columns>)
                SELECT <columns> FROM _stg_xxx
                ON CONFLICT (<key_columns>) DO UPDATE SET
                  col1 = EXCLUDED.col1,
                  col2 = EXCLUDED.col2, ...
       d. Si mode == MERGE:
            - Valider key_columns.
            - Si PG >= 15: instruction native MERGE INTO.
            - Si PG < 15: CTE combinée UPDATE existing + INSERT missing.
       e. Enregistrer le résultat dans _pyingest_target_loads.
  3. Retourner TargetLoadResultV2 (SUCCEEDED ou ROLLED_BACK en cas d'erreur).
```

---

## 5. Invariants Architecturaux & Sécurité

1. **Isolation Stricte du Domaine & Neutralité :**
   - Aucun import de SQLAlchemy ni de Psycopg dans `domain/targets` ou `ports/targets`.
   - `TargetLoadModeV2` reste un `StrEnum` standard de la bibliothèque Python.
2. **Protection Anti-Injection SQL :**
   - Toutes les colonnes de `key_columns` et `update_columns` doivent être strictement validées par `_validate_identifier` (expression régulière `^[A-Za-z_][A-Za-z0-9_]*$`).
   - L'assemblage SQL doit utiliser les objets `sql.Identifier` et `sql.SQL` de psycopg (ou SQLAlchemy Core construct).
3. **Transactionnalité Absolue :**
   - Une seule transaction PostgreSQL par `load()`.
   - En cas d'exception, `engine.begin()` effectue un `ROLLBACK` total : ni les données de staging, ni la table cible, ni la table de métadonnées ne sont polluées.
4. **Préservation des Symboles Gelés de l'API Publique :**
   - `src/pyingestkit/__init__.py` reste rigoureusement à 11 symboles.
   - `public_targets.__all__` conserve exactement ses 6 symboles de haut niveau (`DatasetTargetV2`, `TargetDescriptorV2`, `TargetLoadModeV2`, `TargetLoadRequestV2`, `TargetLoadResultV2`, `TargetLoadStatusV2`).

---

## 6. Stratégie de Validation & Tests

1. **Tests Unitaires Domaine (`tests/unit/v2/test_target_load_v2.py`) :**
   - Validation de `TargetLoadModeV2.UPSERT` et `MERGE`.
   - Validation des champs `key_columns` et `update_columns` dans `TargetLoadRequestV2` (rejet des chaînes vides, rejet des doublons).
2. **Tests de Génération SQL & Adaptateur (`tests/unit/v2/test_postgres_target_sql_v2.py`) :**
   - Vérification de la construction des requêtes SQL `ON CONFLICT` et `MERGE`.
   - Validation de l'échappement et de la prévention anti-injection.
3. **Tests d'Intégration PostgreSQL Réels (`tests/integration/v2/test_postgres_upsert_merge_e2e.py`) :**
   - Scénario UPSERT : Insertion initiale de 3 lignes -> Ingestion d'un dataset contenant 2 mises à jour et 1 nouvelle ligne -> Vérification du nombre total de lignes (4) et des valeurs mises à jour.
   - Scénario Idempotence : Exécution d'un chargement avec `idempotent=True` -> Seconde exécution identique -> Vérification que la seconde exécution est ignorée (`rows_loaded=0`, diagnostic `skipped_idempotent`).
   - Scénario Rollback : Injection d'une ligne violant une contrainte CHECK en fin de lot de staging -> Vérification que la table cible reste strictement inchangée.
4. **Vérification Globale :**
   - `make quality`, `make architecture-v2`, `make test-v2`, `mkdocs build --strict`.
