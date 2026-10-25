# FEEDBACK-LOT36-01 : Advanced PostgreSQL Target Semantics (UPSERT, MERGE & Staging Transactionnel)

- **Tâche Évaluée :** [`../tasks/TASK-LOT36-01_postgres-upsert-merge-and-staging.md`](../tasks/TASK-LOT36-01_postgres-upsert-merge-and-staging.md)
- **Plan Parent :** [`../plans/2026-10-25_plan-postgres-upsert-merge-and-staging.md`](../plans/2026-10-25_plan-postgres-upsert-merge-and-staging.md)
- **Item Backlog :** [`../backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md`](../backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-25
- **Évaluation Globale :** 🟢 Excellente

---

## 1. Résumé de la Session d'Exécution

Le jalon LOT-36 a doté l'adaptateur cible `PostgresTargetV2` de capacités avancées de réconciliation incrémentale par clé, d'atomicité transactionnelle absolue et de contrôle d'idempotence :
1. **Évolution des Contrats du Domaine Cible (`TargetLoadModeV2` & `TargetLoadRequestV2`)** :
   - Ajout de `TargetLoadModeV2.UPSERT` et `TargetLoadModeV2.MERGE` dans `src/pyingestkit/domain/targets/models.py`.
   - Extension de `TargetLoadRequestV2` avec `key_columns`, `update_columns`, et `idempotent`.
   - Validations d'intégrité pures sans driver de base de données : `key_columns` obligatoires pour `UPSERT`/`MERGE`, non-recouvrement entre clés et colonnes de mise à jour, et calcul automatique de `effective_update_columns`.
2. **Générateur SQL Sécurisé Anti-Injection (`_sql.py`)** :
   - Création de `src/pyingestkit/adapters/postgres/_sql.py` utilisant les primitives `psycopg.sql` pour composer des requêtes paramétrées protégées contre les injections.
   - Support complet de `CREATE TEMP TABLE ... ON COMMIT DROP`, de `INSERT ... ON CONFLICT DO UPDATE / DO NOTHING`, et de `MERGE INTO` (PostgreSQL 15+) avec repli CTE pour PostgreSQL < 15.
3. **Implémentation du Staging Table Pattern (`PostgresTargetV2`)** :
   - Refactorisation de `load()` dans `src/pyingestkit/adapters/postgres/target.py` pour orchestrer la création de table temporaire, le flux streaming `COPY ... FROM STDIN` à plein débit, et la réconciliation SQL ensembliste au sein d'une transaction unique (`with engine.begin()`).
4. **Table Technique d'Audit & Contrôle d'Idempotence (`_pyingest_target_loads`)** :
   - Création automatique et idempotente de la table `_pyingest_target_loads` et de son index composite de déduplication.
   - Court-circuit préventif quand `idempotent=True` si la version exacte du dataset a déjà été matérialisée avec succès, avec diagnostic explicite `target.postgres.skipped_idempotent`.
5. **Couverture de Tests Robuste & Documentation** :
   - Tests unitaires complets du domaine (`test_target_materialization.py`) et du générateur SQL (`test_postgres_target_sql_v2.py`).
   - Tests d'intégration E2E réels sur PostgreSQL local (`test_postgres_upsert_merge_e2e.py`).
   - Guide pratique complet `docs/guides/postgres-upsert-merge-and-staging.md` (intégré à `mkdocs.yml`) avec schéma Mermaid et équivalent ASCII synchronisé.

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Performances & Sécurité du Staging Table Pattern :** Le découpage en staging table `ON COMMIT DROP` + `COPY` + réconciliation SQL permet de bénéficier du débit maximal du protocole `COPY` tout en autorisant l'UPSERT par clé avec un rollback automatique garanti par PostgreSQL en cas d'échec.
2. **Découplage Hexagonal & Pureté des Contrats :** `domain/targets` et `ports/targets` ne dépendent d'aucun driver ni ORM. Les 11 symboles de l'API racine et les 6 symboles publics de `pyingestkit.targets` sont restés rigoureusement intacts.
3. **Double Représentation des Schémas (Mermaid + ASCII) :** Tous les diagrammes de flux intègrent désormais une version ASCII pour un confort visuel maximal dans les terminaux et éditeurs sans rendu web.
4. **Contrôles Qualité au Vert :** 384 tests passants, `make quality` sans avertissement, mypy strict sur 107 fichiers sources, et intégration PostgreSQL réelle validée.

---

## 3. Frictions & Difficultés Rencontrées (Points de Douleur)

1. **Règle Ruff BLE001 (Blind Exception) :**
   - Lors de la vérification initiale de `_is_idempotent_duplicate`, l'utilisation de `except Exception:` a été relevée par Ruff.
   - *Résolution :* Remplacement immédiat par le tuple explicite d'exceptions attendues `except (PsycopgError, SQLAlchemyError, OSError):`.
2. **Formatage Automatique Ruff :**
   - Des retours à la ligne dans `_sql.py` et `target.py` ont nécessité un passage automatique de `ruff format` pour s'aligner sur la ligne de conduite du repo.

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

- **Invariance de `TargetLoadResultV2` lors du Saut d'Idempotence :** Le contrat `TargetLoadResultV2` requiert `rows_loaded == rows_input` pour un résultat avec statut `SUCCEEDED`. Pour respecter cet invariant lorsque `idempotent=True` saute l'exécution, `rows_loaded` renvoie la totalité des lignes du dataset déjà matérialisées, tandis que le diagnostic informatif porte le code `target.postgres.skipped_idempotent` et `reason="idempotent_duplicate"`.
- **Validation Systématique des Noms de Colonnes Clés :** Chaque identifiant présent dans `key_columns` et `update_columns` est validé à la fois par le modèle de domaine (non-vide, unique, non-recouvrement) et par l'adaptateur PostgreSQL (`_validate_identifier`) avant d'être encapsulé dans un `sql.Identifier()`.

---

## 5. Leçons Apprises & Actions pour la Suite

1. **Générateur SQL Dédié :** Isoler la syntaxe SQL dans `_sql.py` s'est avéré particulièrement payant pour tester unitairement toutes les combinaisons SQL (versions de PostgreSQL, clés simples et composites, mise à jour sélective ou globale) sans nécessiter de serveur de base de données actif.
2. **Prochaine étape :** Finaliser la revue formelle de clôture de lot (`docs/build/reviews/2026-10-25_lot36_postgres-upsert-merge-and-staging-review.md`), mettre à jour `TASK-LOT36-01` et `TODOS.md` à `✅ DONE`, commiter, pousser la branche, ouvrir la PR et la fusionner sur `main`.
