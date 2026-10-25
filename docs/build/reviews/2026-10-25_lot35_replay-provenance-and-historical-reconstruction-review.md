# Revue de Qualification & Clôture Formelle : LOT-35 Provenance Replay & Historical Reconstruction

- **Jalon / LOT :** LOT-35 : Provenance Replay & Historical Ingestion Reconstruction
- **Date de la Revue :** 2026-10-25
- **Réviseur / Auditeur :** Thomas Awounfouet / Antigravity
- **Statut de Clôture :** ✅ **APPROUVÉ POUR MERGE & RELEASE**
- **Plan Parent :** [`docs/build/plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md`](../plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md`](../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md)
- **Branche :** `feat/replay-provenance-and-historical-reconstruction`

---

## 1. Résumé Exécutif & Périmètre Livré

Le lot **LOT-35** a livré le sous-système de reconstruction historique et de replay de provenance pour PyIngestKit V2 :
1. **Modèle de Domaine Immuable de Lignage Causal (`ReplayLineage`)** : Modèle gelé dans `src/pyingestkit/domain/replay/models.py` capturant `lineage_id`, `source_run_id`, `replay_run_id`, `dataset_id`, `version_id`, checksums SHA-256 RAW, `matched`, et statut `published`.
2. **Ports Découplés de Résolution & de Lignage** :
   - `ReplayProvenanceResolver` (`src/pyingestkit/ports/replay.py`) pour la réhydratation automatique des `ReplayRequest`.
   - `ReplayLineageLedger` (`src/pyingestkit/ports/replay.py`) pour l'enregistrement et le requêtage du lignage causal sans toucher à l'interface gelée de `PublicationLedger`.
3. **Résolveur Automatique de Provenance (`DefaultReplayProvenanceResolver`)** : Implémenté dans `src/pyingestkit/application/resolver.py` avec réhydratation contextuelle des artefacts et définitions et sanitisation sécurisée des paramètres sensibles (`sanitize_parameter_overrides`).
4. **Conservation des Métadonnées RAW au Runtime** : Enrichissement de `IngestionRuntime` (`runtime.py`) pour capturer `source_run_id`, `source_raw_artifact_id`, `source_raw_checksum`, `source_raw_locator`, `source_raw_namespace`, et `source_raw_resource_id` dans chaque référence de version.
5. **Replay Service V2 & CAS Publication** : Extension de `ReplayServiceV2` avec enregistrement automatique du lignage et promotion atomique de publication via `publish_replay(result, publisher=...)`.
6. **Support Multi-Ledgers (`MemoryPublicationLedger` & `PostgresPublicationLedger`)** :
   - Création de la table `pyingestkit_v2_replay_lineage` dans PostgreSQL.
   - Implémentation complète de `ReplayLineageLedger` sur les deux adaptateurs avec détection des conflits d'empreinte et transition d'état atomique `published=False -> True`.
7. **CLI Modernisée `pik replay`** : Support des options `--dataset` (`-d`), `--version` (`-v`), `--publish`, et `--json` avec affichage Rich et rétrocompatibilité V1 stricte garantie.
8. **Documentation & Validation** : Guide utilisateur `docs/guides/historical-replay-and-provenance.md`, suite complète de tests unitaires, de conformité et de CLI.

---

## 2. Grille d'Audit de Conformité

| Domaine d'Audit | Critère Vérifié | Évaluation | Preuve / Observation |
| :--- | :--- | :--- | :--- |
| **Domaine & Immuabilité** | `ReplayLineage` valide strictement ses attributs et horodatages conscients | Conforme ✅ | `test_replay_lineage_validation` validé |
| **Sécurité des Paramètres** | `sanitize_parameter_overrides` masque les tokens et credentials | Conforme ✅ | `test_sanitize_parameter_overrides` validé |
| **Résolution de Provenance** | `DefaultReplayProvenanceResolver` réhydrate depuis version et run | Conforme ✅ | `test_resolver_from_version_...` validé |
| **Service Replay & CAS** | `ReplayServiceV2` exécute sans source live et publie en CAS | Conforme ✅ | `test_replay_service_executes_...` validé |
| **Conformité des Ledgers** | `MemoryPublicationLedger` & `PostgresPublicationLedger` implémentent le protocole | Conforme ✅ | `test_ledger_replay_conformance` validé |
| **CLI V2 Provenance** | `pik replay -d <dataset> -v <version> [--publish] [--json]` | Conforme ✅ | `test_replay_cli_v2.py` (4/4 tests passés) |
| **Rétrocompatibilité V1** | Signature et comportement de `replay_command` préservés | Conforme ✅ | `test_replay_cli.py` 100% vert |
| **Architecture Hexagonale** | 79 tests d'architecture verts sans dépendance illégale | Conforme ✅ | `make architecture-v2` validé en 1.34s |
| **Qualité & Typage** | Zéro erreur Ruff et Mypy sur l'ensemble de la couche V2 | Conforme ✅ | 106 fichiers vérifiés (`mypy` vert, `ruff` vert) |
| **Documentation Stricte** | `mkdocs build --strict` compile avec le nouveau guide | Conforme ✅ | Guide intégré dans `mkdocs.yml`, compile en 2.87s |

---

## 3. Points d'Arbitrage Validés

1. **Isolation du Protocole `ReplayLineageLedger` :** En le plaçant dans `ports/replay.py` plutôt qu'en élargissant `PublicationLedger` dans `ports/governance.py`, la fixture gelée du contrat LOT-23 (`tests/contract/fixtures/governance_v2_1_alpha1.json`) demeure 100% conforme sans compromis.
2. **Transition Contrôlée de l'État de Publication :** Le modèle `ReplayLineage` est immuable à l'exception de la promotion `published=False -> True` lors d'un appel réussi à `publish_replay`. Les adaptateurs mémoire et PostgreSQL garantissent qu'aucune modification d'attribut causal (run IDs, checksums, dataset) n'est permise.
3. **Inférence Robuste du Namespace RAW :** Prise en charge transparente des locators `file://` et `s3://` avec conservation explicite de `source_raw_namespace` et `source_raw_resource_id` dans les métadonnées de version.

---

## 4. Dettes Techniques Résiduelles & Évolutions Futures

- Aucun résidu technique identifié sur ce lot. L'ensemble des 8 lots planifiés de PyIngestKit (LOT-31 à LOT-35) est désormais réalisé à 100%.

---

## 5. Décision Formelle de Livraison

La conformité technique, fonctionnelle et architecturale du lot est **validée sans réserve**.
Le code est **approuvé pour merge dans `main`**.
