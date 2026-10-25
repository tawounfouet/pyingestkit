# Analyse Technique & Architecture : Provenance Replay & Reconstruction Historique (LOT-35)

- **Date :** 2026-10-25
- **Auteur :** Antigravity / Pair Programming
- **Item Backlog :** [`docs/build/backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md`](../build/backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../roadmap/post-2.0-scope-review.md) (Section 3.2)
- **LOT Cible :** LOT-35 (v2.2.0)
- **Références amont :**
  - [`docs/rfc/RFC-001-publication-lifecycle-governance.md`](../rfc/RFC-001-publication-lifecycle-governance.md)
  - [`../../../pytransformkit`](../../../pytransformkit)
  - [`../../../pyworkflowkit`](../../../pyworkflowkit)

---

## 1. Contexte & Problématique

Dans l'architecture de PyIngestKit, le replay strict à partir d'artefacts bruts durables (**RAW**) a été introduit au jalon LOT-11 (`ReplayServiceV2` dans `src/pyingestkit/application/replay.py`). Ce mécanisme garantit le premier invariant non-négociable : **un replay n'est pas une réacquisition live** (aucun appel n'est émis vers l'API ou le stockage source externe).

Cependant, plusieurs lacunes structurelles subsistent pour l'usage opérationnel en production et l'audit réglementaire :

1. **Saisie manuelle fastidieuse de `ReplayRequest` :** Actuellement, le consommateur doit instancier manuellement l'objet `ReplayRequest`, ce qui exige de connaître au préalable l'objet `ArtifactReference` exact de l'artefact RAW et de reconstruire à la main l'objet `IngestionDefinition`.
2. **Absence de résolution automatique à partir de l'identité de version :** Lorsqu'un data engineer ou un auditeur constate une anomalie sur une version de dataset publiée `vX` (ou un `version_id`), il n'existe pas de service de lookup automatique capable de remonter du dataset versionné vers son run source d'origine et son empreinte RAW.
3. **Absence de persistance de la lignée de replay (*Replay Lineage*) :** Bien qu'un nouveau run ID soit alloué (`replay_run_id != source_run_id`), la relation de parenté causale (`source_run_id ──replayed_by──> replay_run_id`) n'est pas consignée de manière durable dans le `PublicationLedger` (ni en mémoire, ni sous PostgreSQL).
4. **Déconnexion de la publication conditionnelle :** À l'issue d'un replay concluant (`matched=True`), le pipeline ne propose pas de passerelle formelle vers le protocole de publication CAS (`compare_and_publish`) pour promouvoir le résultat de manière sécurisée.
5. **Dette V1 dans la CLI `pik replay` :** La commande `pik replay` invoque encore le runner V1 historique au lieu de s'appuyer sur le moteur V2 étendu.

---

## 2. Benchmark : PyIngestKit vs Écosystème & Packages Frères

| Capacité de Replay & Provenance | PyIngestKit V2 (Actuel) | PyTransformKit | PyWorkflowKit / Standards (OpenLineage / PROV) | Standard Cible PyIngestKit (LOT-35) |
| :--- | :--- | :--- | :--- | :--- |
| **Source de Replay** | Artefact RAW durable (`ArtifactReference`) | Tables d'événements delta | Snapshots d'état de DAG | **Artefact RAW immuable avec preuve SHA-256** |
| **Résolution Automatique** | Manuelle (l'appelant fournit tout) | Par version de contrat | Par run identifier | **Lookup automatique via `version_id` ou `run_id`** |
| **Restauration Définition** | Manuelle dans le code client | Inspectée depuis le schéma | Rechargée depuis le registry | **Restauration sécurisée avec redaction des secrets** |
| **Traçabilité / Lignée** | Seuls les métadonnées de RAW sont marquées | Lignée de transformation | Graphe de causalité parent-enfant | **Événement `REPLAY_EXECUTED` dans le `PublicationLedger`** |
| **Publication post-replay** | `publish=False` forcé sans CAS | Versioning de sortie | Promotion explicite | **Publication CAS explicite via `ConditionalDatasetPublisher`** |

---

## 3. Analyse des Options Architecturales

### Option A : Replay Ad-hoc en mémoire sans extension de Ledger
- Conserver `ReplayServiceV2` tel quel et laisser l'orchestrateur externe (Airflow/Dagster) gérer les correspondances et la persistance de l'historique.
- *Inconvénients :* Rupture de la promesse de robustesse de PyIngestKit ; perte de traçabilité en cas de crash de l'orchestrateur ; impossible de prouver la provenance cryptographique lors d'un audit de conformité.

### Option B : Architecture Intégrée de Provenance & Lignée Replay (Recommandée)
1. **Création du `ReplayProvenanceResolver` (Port & Service) :**
   - Capable d'inspecter un `DatasetVersionReference` ou un `IngestionRunId` pour extraire automatiquement la référence du RAW d'origine et la configuration d'ingestion.
2. **Enrichissement du domaine de Replay (`ReplayLineage`) :**
   - Modélisation explicite d'un enregistrement immuable de causalité liant le run source, le run de replay, les empreintes SHA-256 et le statut de concordance (`matched`).
3. **Extension du `PublicationLedger` :**
   - Ajout d'une table SQL `pyingestkit_v2_replay_lineage` (et équivalent en mémoire) pour interroger l'historique des replays (`list_replays_for_run`, `list_replays_for_dataset`).
4. **Publication Conditionnelle Gouvernée Post-Replay :**
   - Méthode explicite pour soumettre le résultat de replay à `compare_and_publish`.
5. **Modernisation de `pik replay` :**
   - Intégration complète dans la CLI avec affichage riche (`rich`) et format `--json`.

---

## 4. Diagramme d'Architecture Cible

```text
  +─────────────────────────────────────────────────────────────+
  |                        Replay Intent                        |
  |         (via version_id, dataset_id ou source_run_id)       |
  +─────────────────────────────────────────────────────────────+
                                │
                                ▼
         +───────────────────────────────────────────────+
         |           ReplayProvenanceResolver            |
         |  - Résolution de l'ArtifactReference RAW      |
         |  - Restauration de l'IngestionDefinition     |
         |  - Masquage des paramètres sensibles          |
         +───────────────────────────────────────────────+
                                │
                                ▼
         +───────────────────────────────────────────────+
         |                ReplayServiceV2                |
         |  - Matérialisation du RAW de replay           |
         |  - Exécution décodeur + validation (zéro I/O) |
         |  - Comparaison des empreintes (matched: bool) |
         +───────────────────────────────────────────────+
                                │
                                ▼
         +───────────────────────────────────────────────+
         |              PublicationLedger                |
         |   Enregistrement immuable de ReplayLineage    |
         |  (source_run_id -> replay_run_id + SHA256)    |
         +───────────────────────────────────────────────+
                                │
                                ▼ (si demandé explicitement)
         +───────────────────────────────────────────────+
         |          ConditionalDatasetPublisher          |
         |       Compare-and-Swap (CAS) Publication      |
         +───────────────────────────────────────────────+
```

---

## 5. Invariants d'Architecture Non-Négociables

1. **Isolation stricte de la source :** Aucun appel réseau ou filesystem vers le connecteur source d'origine lors d'un replay.
2. **Identité de run disjointe :** `replay_run_id != source_run_id`.
3. **Preuve cryptographique :** Le RAW de replay doit posséder un hash SHA-256 strictement identique à l'artefact source.
4. **Explicitation de la publication :** Aucune publication de dataset versionné ne doit être effectuée sans demande explicite (`publish=True` avec CAS).
5. **Immuabilité de l'API racine :** Les 11 symboles gelés de `pyingestkit.__init__` ne doivent pas être modifiés. Les nouvelles capacités de replay et provenance s'exposent via le namespace qualifié `pyingestkit.replay` et `pyingestkit.governance`.

---

## 6. Conclusion & Recommandation

L'Option B respecte scrupuleusement l'architecture hexagonale et les contrats V2 gelés, tout en comblant le besoin fonctionnel du backlog `ITEM-005`. Elle fournit une traçabilité de bout en bout pour le jalon v2.2.0.
