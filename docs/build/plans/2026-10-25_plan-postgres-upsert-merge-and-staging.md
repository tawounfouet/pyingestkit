# Plan d'Implémentation : Sémantique Cible PostgreSQL Avancée (UPSERT, MERGE & Staging Transactionnel) — LOT-36

- **Projet :** PyIngestKit
- **Statut :** READY
- **Date :** 2026-10-25
- **Auteur :** Antigravity / Pair Programming
- **Item Backlog :** [`docs/build/backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md`](../backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md)
- **Document source :** [`docs/analyses/2026-10-25_postgres-upsert-merge-and-staging-analysis.md`](../../analyses/2026-10-25_postgres-upsert-merge-and-staging-analysis.md)
- **Cadrage préalable :** [`docs/analyses/cadrage/2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md`](../../analyses/cadrage/2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md)
- **Branche cible :** `feat/postgres-upsert-merge-and-staging`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation structure la livraison du jalon **LOT-36** (v2.2.0) pour doter PyIngestKit V2 de capacités industrielles de synchronisation incrémentale, de déduplication par clé et de traçabilité d'idempotence au niveau de l'adaptateur de matérialisation cible PostgreSQL :

### Capacités Livrées
1. **Évolution des Contrats du Domaine Cible (`TargetLoadModeV2` & `TargetLoadRequestV2`)** :
   - Ajout des modes portables `TargetLoadModeV2.UPSERT = "upsert"` et `TargetLoadModeV2.MERGE = "merge"`.
   - Extension de `TargetLoadRequestV2` avec `key_columns: tuple[str, ...] = ()`, `update_columns: tuple[str, ...] = ()`, et `idempotent: bool = False`.
   - Validation stricte d'intégrité : `key_columns` obligatoires pour `UPSERT` et `MERGE`, validation des identifiants et des dépendances de schéma sans aucune dépendance vers un driver de base de données.
2. **Implémentation du Staging Table Pattern Transactionnel (`PostgresTargetV2`)** :
   - Création dynamique d'une table temporaire isolée : `CREATE TEMP TABLE _stg_<uuid> (LIKE <destination> INCLUDING DEFAULTS) ON COMMIT DROP;`.
   - Alimentation massive via `COPY ... FROM STDIN` dans la table temporaire (débit maximal sans verrou long sur la table de production).
3. **Réconciliation SQL Atomique (`UPSERT` & `MERGE`)** :
   - Mode `UPSERT` : `INSERT INTO <destination> SELECT ... FROM _stg_<uuid> ON CONFLICT (<key_columns>) DO UPDATE SET ...` (ou `DO NOTHING` si toutes les colonnes sont des clés).
   - Mode `MERGE` : Instruction native `MERGE INTO` pour PostgreSQL 15+ ou CTE combinée d'insertion / mise à jour atomique pour les versions antérieures.
4. **Table Technique de Traçabilité & Contrôle d'Idempotence Cible (`_pyingest_target_loads`)** :
   - Création idempotente de la table `_pyingest_target_loads` et de son index composite `(target_id, destination, dataset_version_id, mode)`.
   - Contrôle d'idempotence préventif : si `idempotent=True` et qu'un chargement a déjà réussi pour la version exacte, retour immédiat sans ré-exécution du flux de données avec diagnostic `target.postgres.skipped_idempotent`.
5. **Couverture de Tests Robuste & Sécurité Anti-Injection** :
   - Validation de l'échappement systématique des identifiants SQL.
   - Tests unitaires et d'intégration de bout en bout sur PostgreSQL réel (E2E).

### Hors Périmètre (Exclusions Délibérées)
- Pas de modification de l'API racine gelée (`src/pyingestkit/__init__.py`) : exposition via `pyingestkit.targets.v2` et `pyingestkit.adapters.postgres`.
- `public_targets.__all__` conserve strictement ses 6 symboles portables de haut niveau.
- Pas de logique métier spécifique à un schéma applicatif particulier (la détection de conflits et les mappings reposent sur les contrats fournis).

---

## 2. Diagramme d'Architecture & Flux de Données

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| FLUX D'EXÉCUTION DU CHARGEMENT POSTGRESQL AVANCÉ (STAGING + UPSERT/MERGE + IDEMPOTENCE)           |
|                                                                                                   |
|  [ TargetLoadRequestV2 ]                                                                          |
|       │ (target_id, destination, dataset_version, mode=UPSERT/MERGE, key_columns, idempotent=True)  |
|       ▼                                                                                           |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | PostgresTargetV2.load()                                                                     |  |
|  |                                                                                             |  |
|  |  1. Contrôle d'Idempotence :                                                                |  |
|  |     Si request.idempotent == True :                                                         |  |
|  |       SELECT 1 FROM _pyingest_target_loads WHERE target_id=? AND destination=?              |  |
|  |                                              AND dataset_version_id=? AND mode=?            |  |
|  |                                              AND status='succeeded'                         |  |
|  |       -> Si trouvé : Retour TargetLoadResultV2 (SUCCEEDED, skipped_idempotent)              |  |
|  |                                                                                             |  |
|  |  2. Ouverture de Transaction Unique (engine.begin()) :                                      |  |
|  |     │                                                                                       |  |
|  |     ├── a. Validation du Schéma & Identifiants (anti-injection SQL)                         |  |
|  |     │                                                                                       |  |
|  |     ├── b. Mode standard (APPEND / TRUNCATE_LOAD / REPLACE) :                               |  |
|  |     │      Exécution directe via COPY (chemin éprouvé LOT-14)                               |  |
|  |     │                                                                                       |  |
|  |     └── c. Mode avancé (UPSERT / MERGE) :                                                   |  |
|  |            │                                                                                |  |
|  |            ├── 1. CREATE TEMP TABLE _stg_<uuid> (LIKE <target> INCLUDING DEFAULTS)          |  |
|  |            │      ON COMMIT DROP;                                                           |  |
|  |            │                                                                                |  |
|  |            ├── 2. COPY _stg_<uuid> (...) FROM STDIN (flux streaming psycopg)                |  |
|  |            │                                                                                |  |
|  |            └── 3. Réconciliation SQL Atomique :                                             |  |
|  |                   - UPSERT : INSERT INTO <target> SELECT * FROM _stg_<uuid>                 |  |
|  |                              ON CONFLICT (<keys>) DO UPDATE SET ...                         |  |
|  |                   - MERGE  : MERGE INTO <target> USING _stg_<uuid> ...                      |  |
|  |                                                                                             |  |
|  |  3. Enregistrement d'Audit :                                                                |  |
|  |     INSERT INTO _pyingest_target_loads (load_id, target_id, destination,                    |  |
|  |                                        dataset_version_id, mode, rows_loaded, status, ...)  |  |
|  |                                                                                             |  |
|  |  4. COMMIT ou ROLLBACK global :                                                             |  |
|  |     En cas d'exception : ROLLBACK total (la table temporaire disparaît, la cible est intacte)  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|       │                                                                                           |
|       ▼                                                                                           |
|  [ TargetLoadResultV2 ] (SUCCEEDED ou ROLLED_BACK)                                                |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
src/pyingestkit/
├── domain/
│   └── targets/
│       ├── __init__.py                     # [MAINTIEN] Export des symboles de domaine
│       └── models.py                       # [MODIFICATION] Ajout UPSERT/MERGE, key_columns, update_columns, idempotent
├── adapters/
│   └── postgres/
│       ├── __init__.py                     # [MAINTIEN] Export PostgresTargetV2
│       ├── _sql.py                         # [CRÉATION] Générateur SQL sécurisé (CREATE TEMP, ON CONFLICT, MERGE)
│       └── target.py                       # [MODIFICATION] Intégration staging, réconciliation, _pyingest_target_loads

tests/
├── unit/v2/
│   ├── test_target_materialization.py      # [MODIFICATION] Validation des nouveaux champs et contraintes TargetLoadRequestV2
│   └── test_postgres_target_sql_v2.py      # [CRÉATION] Tests unitaires du constructeur SQL (anti-injection, syntaxes)
├── integration/v2/
│   ├── test_postgres_target_v2.py          # [MAINTIEN] Tests de non-régression des modes existants
│   └── test_postgres_upsert_merge_e2e.py   # [CRÉATION] Tests d'intégration réels E2E (UPSERT, MERGE, Staging, Idempotence)

docs/
├── analyses/
│   └── 2026-10-25_postgres-upsert-merge-and-staging-analysis.md # [CRÉÉ] Analyse technique préliminaire
├── build/
│   ├── backlog/
│   │   └── ITEM-006_postgresql-target-upsert-merge-and-staging.md # [RÉFÉRENCE] Item de backlog
│   ├── plans/
│   │   └── 2026-10-25_plan-postgres-upsert-merge-and-staging.md # [CE FICHIER] Plan d'implémentation
│   └── tasks/
│       ├── TASK-LOT36-01_postgres-upsert-merge-and-staging.md   # [CRÉATION] Tâche d'exécution
│       └── TODOS.md                                             # [MODIFICATION] Enregistrement de la tâche
└── guides/
    └── postgres-upsert-merge-and-staging.md                     # [CRÉATION] Guide pratique d'utilisation
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Domaine Cible : Modes & Requête de Chargement
**Fichier à modifier :** `src/pyingestkit/domain/targets/models.py`

1. **Extension de `TargetLoadModeV2`** :
   ```python
   class TargetLoadModeV2(StrEnum):
       APPEND = "append"
       TRUNCATE_LOAD = "truncate_load"
       REPLACE = "replace"
       UPSERT = "upsert"      # LOT-36
       MERGE = "merge"        # LOT-36
   ```
2. **Extension de `TargetLoadRequestV2`** :
   ```python
   key_columns: tuple[str, ...] = ()
   update_columns: tuple[str, ...] = ()
   idempotent: bool = False
   ```
3. **Règles de validation dans `__post_init__`** :
   - `idempotent` doit être un booléen (`isinstance(self.idempotent, bool)`).
   - `key_columns` et `update_columns` doivent être des tuples de chaînes non-vides et sans doublons.
   - Si `mode in (TargetLoadModeV2.UPSERT, TargetLoadModeV2.MERGE)` :
     - `key_columns` ne peut pas être vide : lever `ValueError("TargetLoadRequestV2 requires key_columns for UPSERT or MERGE.")`.
     - Tous les éléments de `key_columns` doivent faire partie des colonnes résolues (`resolved_columns`).
   - Si `update_columns` est fourni :
     - Tous les éléments doivent faire partie de `resolved_columns`.
     - Aucune colonne de `update_columns` ne doit figurer dans `key_columns` (les colonnes clés ne sont pas mises à jour par conflit).
   - Définir une propriété `effective_update_columns -> tuple[str, ...]` qui renvoie `update_columns` si non-vide, ou l'ensemble des colonnes résolues hors clés sinon.

---

### Phase 2 — Constructeur de Requêtes SQL Sécurisé (`_sql.py`)
**Fichier à créer :** `src/pyingestkit/adapters/postgres/_sql.py`

Isoler la logique de composition SQL avec les primitives `psycopg.sql` pour garantir l'immunité totale contre les injections SQL et faciliter les tests unitaires sans base active :
1. `create_temp_staging_table_sql(staging_table: str, target_schema: str | None, target_table: str) -> Composed` :
   Génère `CREATE TEMP TABLE {staging} (LIKE {target} INCLUDING DEFAULTS) ON COMMIT DROP;`.
2. `build_upsert_reconciliation_sql(target_schema: str | None, target_table: str, staging_table: str, columns: tuple[str, ...], key_columns: tuple[str, ...], update_columns: tuple[str, ...]) -> Composed` :
   - Si `update_columns` est non-vide :
     ```sql
     INSERT INTO {target} ({columns})
     SELECT {columns} FROM {staging}
     ON CONFLICT ({key_columns}) DO UPDATE SET
       col = EXCLUDED.col, ...
     ```
   - Si `update_columns` est vide (cas où toutes les colonnes constituent la clé primaire) :
     ```sql
     INSERT INTO {target} ({columns})
     SELECT {columns} FROM {staging}
     ON CONFLICT ({key_columns}) DO NOTHING
     ```
3. `build_merge_reconciliation_sql(target_schema: str | None, target_table: str, staging_table: str, columns: tuple[str, ...], key_columns: tuple[str, ...], update_columns: tuple[str, ...], server_version: int) -> Composed` :
   - Pour PostgreSQL >= 15 (version >= 150000) :
     ```sql
     MERGE INTO {target} AS t
     USING {staging} AS s
     ON t.k1 = s.k1 AND ...
     WHEN MATCHED THEN
       UPDATE SET col = s.col, ...
     WHEN NOT MATCHED THEN
       INSERT ({columns}) VALUES (s.c1, s.c2, ...)
     ```
   - Pour PostgreSQL < 15 :
     Générer la CTE d'insertion/mise à jour atomique équivalente.
4. `build_ensure_metadata_table_sql(schema: str | None) -> Composed` :
   Génère la création idempotente de `_pyingest_target_loads`.

---

### Phase 3 — Adaptateur PostgreSQL : Staging, Exécution & Idempotence
**Fichier à modifier :** `src/pyingestkit/adapters/postgres/target.py`

1. **Validation pré-vol des identifiants** :
   - Valider chaque colonne de `key_columns` et `update_columns` avec `_validate_identifier`.
2. **Vérification d'idempotence préventive** :
   - Si `request.idempotent is True` :
     - Vérifier la présence d'une entrée `status = 'succeeded'` pour `(target_id, destination, dataset_version_id, mode.value)`.
     - Si présente, retourner un `TargetLoadResultV2` avec `status = TargetLoadStatusV2.SUCCEEDED`, `rows_loaded = len(request.representation)`, et un diagnostic informatif `target.postgres.skipped_idempotent`.
3. **Branchement de chargement dans `load()`** :
   - Si `request.mode in (TargetLoadModeV2.UPSERT, TargetLoadModeV2.MERGE)` :
     - Générer un nom de table temporaire unique `_stg_` + `uuid4().hex[:12]`.
     - Exécuter la création de la table temporaire.
     - Émettre le flux `COPY` dans la table temporaire via `_copy_to_table(connection, staging_table_name, request)`.
     - Exécuter la réconciliation SQL appropriée (`UPSERT` ou `MERGE`).
   - Si mode standard (`APPEND`, `TRUNCATE_LOAD`, `REPLACE`) : conserver le chemin direct existant.
4. **Enregistrement de la trace de chargement** :
   - À l'issue du chargement réussi dans la même transaction, insérer une ligne dans `_pyingest_target_loads`.
5. **Gestion atomique des erreurs & rollback** :
   - En cas d'échec (`_PostgresProviderError`, `SQLAlchemyError`), le bloc `with engine.begin()` rollback intégralement la transaction, détruisant la table temporaire et annulant toute modification.

---

### Phase 4 — Tests Unitaires
**Fichiers :**
- `tests/unit/v2/test_target_materialization.py` :
  - Validation du constructeur `TargetLoadRequestV2` avec `key_columns` vides sous `UPSERT`/`MERGE` (doit lever `ValueError`).
  - Validation du calcul de `effective_update_columns`.
  - Validation du flag `idempotent`.
- `tests/unit/v2/test_postgres_target_sql_v2.py` :
  - Test de composition des requêtes `ON CONFLICT DO UPDATE` et `DO NOTHING`.
  - Test de composition des requêtes `MERGE INTO` (PG15+) et CTE.
  - Vérification de l'échappement anti-injection sur les noms de colonnes et de tables.

---

### Phase 5 — Tests d'Intégration Réels E2E
**Fichier à créer :** `tests/integration/v2/test_postgres_upsert_merge_e2e.py`

Exécuté sur PostgreSQL réel via `PYINGEST_TEST_POSTGRES_DSN` :
1. **Scénario 1 : UPSERT incrémental avec clé primaire** :
   - Insertion de `[("1", "Alice"), ("2", "Bob")]`.
   - Ingestion en mode `UPSERT` de `[("2", "Bob Updated"), ("3", "Charlie")]`.
   - Vérification du résultat final : `[("1", "Alice"), ("2", "Bob Updated"), ("3", "Charlie")]` (3 lignes au total).
2. **Scénario 2 : MERGE complet avec clés composites** :
   - Table avec clé composite `(org_id, user_id)`.
   - Insertion et mise à jour conditionnelle via mode `MERGE`.
3. **Scénario 3 : Idempotence active (`idempotent=True`)** :
   - Premier chargement : `status=SUCCEEDED`, insertion dans `_pyingest_target_loads`.
   - Second chargement identique avec `idempotent=True` : détection d'idempotence, aucune ré-insertion, retour immédiat avec diagnostic `skipped_idempotent`.
4. **Scénario 4 : Atomicité Staging & Rollback en cas d'erreur de contrainte** :
   - Tentative d'UPSERT contenant une valeur violant une contrainte `CHECK`.
   - Constat du `ROLLED_BACK`, vérification que la table cible n'a pas été altérée et que la table temporaire a été purgée.

---

### Phase 6 — Documentation Utilisateur
**Fichier à créer :** `docs/guides/postgres-upsert-merge-and-staging.md`

- Guide pratique pour l'ingestion incrémentale PostgreSQL.
- Exemples de configuration pour pipelines CDC et déduplication d'événements.
- Bonnes pratiques d'indexation des colonnes clés pour les performances d'UPSERT.

---

### Phase 7 — Validation & Qualification Globale

Commandes de qualification :
```bash
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PYINGEST_TEST_POSTGRES_DSN="postgresql://postgres@localhost:5432/postgres" PATH="/opt/miniconda3/bin:$PATH" pytest tests/integration/v2/test_postgres_target_v2.py tests/integration/v2/test_postgres_upsert_merge_e2e.py
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```

---

## 5. Critères d'Acceptation & Validation

- [ ] `TargetLoadModeV2` intègre `UPSERT` et `MERGE` sans altérer l'API publique ni casser les modes existants.
- [ ] `TargetLoadRequestV2` valide rigoureusement `key_columns`, `update_columns`, et `idempotent`.
- [ ] Le Staging Table Pattern est implémenté avec `CREATE TEMP TABLE ... ON COMMIT DROP` et `COPY`.
- [ ] La réconciliation `UPSERT` (`ON CONFLICT DO UPDATE` / `DO NOTHING`) est fonctionnelle et protégée contre les injections.
- [ ] La réconciliation `MERGE` fonctionne sous PostgreSQL 15+ (avec repli CTE si nécessaire).
- [ ] La table technique `_pyingest_target_loads` trace les chargements et prévient les doublons si `idempotent=True`.
- [ ] Tous les tests unitaires et d'intégration E2E sur PostgreSQL réel passent à 100 %.
- [ ] `make quality`, `make architecture-v2`, `make test-v2` et `mkdocs build --strict` s'exécutent avec zéro avertissement.
