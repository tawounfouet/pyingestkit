# FEEDBACK-LOT35-01 : Provenance Replay & Historical Ingestion Reconstruction

- **Tâche Évaluée :** [`../tasks/TASK-LOT35-01_replay-provenance-and-historical-reconstruction.md`](../tasks/TASK-LOT35-01_replay-provenance-and-historical-reconstruction.md)
- **Plan Parent :** [`../plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md`](../plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md)
- **Item Backlog :** [`../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md`](../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-25
- **Évaluation Globale :** 🟢 Excellente

---

## 1. Résumé de la Session d'Exécution

L'exécution du LOT-35 a apporté l'ensemble des capacités de replay strict et de reconstruction historique causale à PyIngestKit V2 :
1. **Modèle de Domaine Immuable de Lignage Causal (`ReplayLineage`)** : Création de `ReplayLineage` dans `src/pyingestkit/domain/replay/models.py` capturant `lineage_id`, `source_run_id`, `replay_run_id`, `dataset_id`, `version_id`, checksums SHA-256 RAW, `matched`, et statut `published`.
2. **Ports de Résolution & de Persistance du Lignage** : Définition des protocoles `ReplayProvenanceResolver` et `ReplayLineageLedger` dans `src/pyingestkit/ports/replay.py`.
3. **Résolveur Automatique de Provenance (`DefaultReplayProvenanceResolver`)** : Implémentation dans `src/pyingestkit/application/resolver.py` avec reconstruction automatique du `ReplayRequest` depuis la version ou le run historique et sanitisation sécurisée des paramètres (`sanitize_parameter_overrides`).
4. **Conservation des Métadonnées RAW au Runtime** : Enrichissement de `IngestionRuntime` (`runtime.py`) pour enregistrer `source_run_id`, `source_raw_artifact_id`, `source_raw_checksum`, `source_raw_locator`, `source_raw_namespace`, et `source_raw_resource_id` dans la référence de version.
5. **Replay Service V2 & CAS Publication** : Extension de `ReplayServiceV2` avec enregistrement automatique de lignage et promotion atomique de publication via `publish_replay(result, publisher=...)`.
6. **Support Multi-Ledgers (`MemoryPublicationLedger` & `PostgresPublicationLedger`)** : Ajout de la table `pyingestkit_v2_replay_lineage` et implémentation complète de `ReplayLineageLedger` avec détection des conflits et transition d'état `published=False -> True`.
7. **CLI Modernisée `pik replay`** : Ajout des drapeaux `--dataset` (`-d`), `--version` (`-v`), `--publish`, et `--json` avec affichage Rich et 100% de rétrocompatibilité V1.
8. **Documentation Utilisateur & Suite de Tests Complète** : Guide utilisateur `docs/guides/historical-replay-and-provenance.md`, tests unitaires `test_replay_provenance_v2.py`, tests de conformance `test_ledger_replay_conformance.py`, et tests CLI `test_replay_cli_v2.py`.

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Découplage Propre des Protocoles de Port :** La création de `ReplayLineageLedger` dans `ports/replay.py` a évité d'altérer l'interface `PublicationLedger` de `ports/governance.py`, préservant intacte la fixture de gouvernance gelée LOT-23.
2. **Immuabilité & Transition d'État CAS Contrôlée :** Le modèle `ReplayLineage` garantit l'immuabilité de tous les attributs causaux tout en autorisant la promotion contrôlée `published=False -> True` lors d'une publication CAS réussie.
3. **Rétrocompatibilité Totale de la CLI :** Les invocations existantes de `pik replay <run_id>` et `pik replay` continuent d'exécuter la branche V1 sans aucun changement d'argument ni d'effet de bord, tandis que les arguments `--dataset` déclenchent la branche V2 moderne.
4. **Intégrité de la Chaîne d'Outillage :** 373 tests V2 passés, `make quality` et `mypy` 100% au vert sur 106 fichiers sources V2, et `mkdocs build --strict` réussi en 2.8s.

---

## 3. Frictions & Difficultés Rencontrées (Points de Douleur)

1. **Divergence de Namespace pour les Références RAW Réhydratées :** Lors du premier test CLI, `DefaultReplayProvenanceResolver` construisait `ResourceReference` avec le namespace `"pyingestkit.replay"`, rejeté par `FileArtifactStore` qui attend strictement `"pyingestkit.artifact.file"`.
   - *Résolution :* Ajout de l'enregistrement de `source_raw_namespace` et `source_raw_resource_id` dans `IngestionRuntime`, et inférence contextuelle automatique selon le schéma du locator (`file://` -> `"pyingestkit.artifact.file"`, `s3://` -> `"pyingestkit.artifact.s3"`).
2. **Casse de la Valeur de l'Enum `ConditionalPublicationStatus` :** L'assertion dans le test CLI attendait `"SUCCEEDED"`, alors que la valeur string interne de l'enum est en minuscules (`"succeeded"`).
   - *Résolution :* Remplacement de l'évaluation textuelle brute par la comparaison directe de l'enum `is ConditionalPublicationStatus.SUCCEEDED` dans la CLI et mise à jour de l'assertion du test.

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

- **Emplacement du Protocole Ledger Replay :** Choix délibéré de placer `ReplayLineageLedger` dans `src/pyingestkit/ports/replay.py` et d'implémenter ce protocole au sein de `MemoryPublicationLedger` et `PostgresPublicationLedger`. Cela évite toute rupture de contrat d'API publique pour le package de gouvernance gelé.
- **Support des Décideurs et Sources Standards dans la CLI :** Initialisation directe de `JsonDecoder` et `CsvDecoder` dans la CLI V2 pour couvrir immédiatement les formats standards de données locales sans nécessiter de configuration additionnelle.

---

## 5. Leçons Apprises & Actions pour la Suite

1. **Vérifier les invariants de namespace des ResourceReferences :** Dans les architectures hexagonales où les adaptateurs valident le propriétaire de la ressource (`is_relative_to`, `namespace`), toujours propager fidèlement les métadonnées de namespace d'origine.
2. **Prochaine étape :** Finaliser la revue formelle `2026-10-25_lot35_replay-provenance-and-historical-reconstruction-review.md`, marquer la tâche et `TODOS.md` à `DONE`, puis ouvrir la PR et la fusionner sur `main`.
