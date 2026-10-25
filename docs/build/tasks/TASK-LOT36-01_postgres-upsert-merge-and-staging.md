# TASK-LOT36-01 : Adaptateur PostgreSQL UPSERT/MERGE et Staging Transactionnel

- **Statut :** ✅ DONE
- **Plan Parent :** [`docs/build/plans/2026-10-25_plan-postgres-upsert-merge-and-staging.md`](../plans/2026-10-25_plan-postgres-upsert-merge-and-staging.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md`](../backlog/ITEM-006_postgresql-target-upsert-merge-and-staging.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-25
- **Date d'achèvement :** 2026-10-25
- **Branche Git :** `feat/postgres-upsert-merge-and-staging`

---

## 1. Contexte & Objectif Unitaire

Implémenter la sémantique cible avancée pour PostgreSQL dans PyIngestKit V2 (LOT-36) :
1. Élargir les contrats portables `TargetLoadModeV2` (avec `UPSERT` et `MERGE`) et `TargetLoadRequestV2` (avec `key_columns`, `update_columns`, `idempotent`).
2. Créer un constructeur SQL sécurisé (`_sql.py`) pour la gestion des tables temporaires de staging et les requêtes ensemblistes de réconciliation (`ON CONFLICT` et `MERGE`).
3. Implémenter dans `PostgresTargetV2` le pattern Staging Table (`CREATE TEMP TABLE ... ON COMMIT DROP` + `COPY` + réconciliation SQL).
4. Mettre en place la traçabilité et le saut d'idempotence via la table technique `_pyingest_target_loads`.
5. Valider par une suite exhaustive de tests unitaires et de tests d'intégration E2E sur PostgreSQL réel.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/domain/targets/models.py` | Modification | Ajout de `UPSERT`/`MERGE`, `key_columns`, `update_columns`, `idempotent` |
| `src/pyingestkit/adapters/postgres/_sql.py` | Création | Générateur de requêtes SQL sécurisées (staging, upsert, merge, audit) |
| `src/pyingestkit/adapters/postgres/target.py` | Modification | Intégration du staging table pattern, de la réconciliation et de l'idempotence |
| `tests/unit/v2/test_target_materialization.py` | Modification | Tests unitaires des extensions de `TargetLoadRequestV2` |
| `tests/unit/v2/test_postgres_target_sql_v2.py` | Création | Tests unitaires du générateur SQL (anti-injection, syntaxes) |
| `tests/integration/v2/test_postgres_upsert_merge_e2e.py` | Création | Tests d'intégration E2E sur PostgreSQL réel (UPSERT, MERGE, Staging, Idempotence) |
| `docs/guides/postgres-upsert-merge-and-staging.md` | Création | Guide d'utilisation pour l'ingestion incrémentale PostgreSQL |
| `docs/build/tasks/TODOS.md` | Modification | Enregistrement de la tâche opérationnelle |

---

## 3. Checklist d'Exécution

- [x] **Étape 1 :** Étendre `TargetLoadModeV2` et `TargetLoadRequestV2` dans `src/pyingestkit/domain/targets/models.py`.
- [x] **Étape 2 :** Développer le module de composition SQL sécurisé `src/pyingestkit/adapters/postgres/_sql.py`.
- [x] **Étape 3 :** Adapter `PostgresTargetV2` pour gérer les tables temporaires de staging, le flux `COPY` et la réconciliation SQL.
- [x] **Étape 4 :** Intégrer la gestion de la table `_pyingest_target_loads` et le contrôle d'idempotence préventif.
- [x] **Étape 5 :** Rédiger les tests unitaires (`test_target_materialization.py`, `test_postgres_target_sql_v2.py`).
- [x] **Étape 6 :** Rédiger les tests d'intégration réels E2E (`test_postgres_upsert_merge_e2e.py`) et valider contre PostgreSQL local.
- [x] **Étape 7 :** Rédiger le guide d'utilisation `docs/guides/postgres-upsert-merge-and-staging.md`.
- [x] **Étape 8 :** Valider l'ensemble de la suite (`make quality`, `make architecture-v2`, `make test-v2`, `mkdocs build --strict`).
- [x] **Étape 9 :** Rédiger la fiche REX `FEEDBACK-LOT36-01` et la revue formelle de clôture de jalon.

---

## 4. Preuves & Commandes de Validation

```bash
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PYINGEST_TEST_POSTGRES_DSN="postgresql://postgres@localhost:5432/postgres" PYTHONPATH=src:. PATH="/opt/miniconda3/bin:$PATH" pytest tests/integration/v2/test_postgres_upsert_merge_e2e.py
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```

---

## 5. Résultat & Clôture de Tâche

- **Statut final :** ✅ DONE
- **Commit / PR :** [`28b6a75`](https://github.com/tawounfouet/pyingestkit/commit/28b6a75b204bb4ae83655b2d2e8fcab1a3013fc9) (PR [#72](https://github.com/tawounfouet/pyingestkit/pull/72))
- **Fiche REX associée :** [`docs/build/feedback/FEEDBACK-LOT36-01_postgres-upsert-merge-and-staging.md`](../feedback/FEEDBACK-LOT36-01_postgres-upsert-merge-and-staging.md)
- **Revue de lot associée :** [`docs/build/reviews/2026-10-25_lot36_postgres-upsert-merge-and-staging-review.md`](../reviews/2026-10-25_lot36_postgres-upsert-merge-and-staging-review.md)
