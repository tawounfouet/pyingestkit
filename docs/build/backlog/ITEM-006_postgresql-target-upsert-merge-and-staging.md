# ITEM-006 : Sémantique Cible PostgreSQL Avancée (UPSERT, MERGE & Tables de Staging)

- **Statut :** PROPOSED
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** MOYENNE
- **Composant Cible :** PostgreSQL Target Adapter (`src/pyingestkit/adapters/targets/postgresql/`)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../../roadmap/post-2.0-scope-review.md) (Section 3.3)
- **LOT Cible :** LOT-36 (v2.2.0)

---

## 1. Contexte & Problématique Constatée

Actuellement, l'écriture vers PostgreSQL dans PyIngestKit supporte l'insertion directe, mais manque de sémantiques robustes pour les scénarios de chargement incrémental en entreprise :
1. Absence de support formel pour le mode `UPSERT` (`INSERT ... ON CONFLICT DO UPDATE`) et `MERGE`.
2. Absence d'isolation transactionnelle par table de staging (`staging_table -> production_table`).
3. Manque d'enregistrement durable de l'historique de chargement cible pour garantir l'idempotence stricte en cas de re-jeu partiel.

---

## 2. Expression du Besoin & User Story

- **En tant que :** Concepteur de pipeline de données PostgreSQL.
- **Je souhaite :** Définir des stratégies de chargement cible déclaratives (`APPEND`, `UPSERT`, `MERGE`, `REPLACE_PARTITION`) avec passage automatique par table de staging.
- **Afin de :** Garantir que les tables de production ne soient jamais laissées dans un état corrompu ou partiellement chargé lors d'un incident de crash.

---

## 3. Bénéfices Attendus

1. **Idempotence :** Exécutions multiples d'un même run sans duplication de lignes.
2. **Atomicité :** Basculement transactionnel de staging vers production en une seule transaction SQL.
3. **Traçabilité :** Métadonnées d'idempotence stockées dans une table technique `_pyingest_target_loads`.

---

## 4. Invariants & Garde-Fous

- [ ] Séparation nette entre matérialisation directe (propriété de PyIngestKit) et orchestration multi-tables (propriété du workflow externe ou de PyWorkflowKit).
- [ ] Le Core Domain reste 100 % découplé de psycopg/SQLAlchemy.
- [ ] Respect des 11 symboles de l'API racine V2.
