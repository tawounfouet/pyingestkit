# Plan d'Implémentation : Provenance Replay & Reconstruction Historique (LOT-35)

- **Projet :** PyIngestKit
- **Statut :** READY
- **Date :** 2026-10-25
- **Auteur :** Antigravity / Pair Programming
- **Item Backlog :** [`docs/build/backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md`](../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md)
- **Document source :** [`docs/analyses/2026-10-25_replay-provenance-and-historical-reconstruction-analysis.md`](../../analyses/2026-10-25_replay-provenance-and-historical-reconstruction-analysis.md)
- **Branche cible :** `feat/replay-provenance-and-historical-reconstruction`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation structure la livraison du jalon **LOT-35** pour fournir à PyIngestKit une infrastructure complète de traçabilité, de reconstruction historique et de replay gouverné :

### Capacités Livrées
1. **Recherche & Résolution Automatique de Provenance (`ReplayProvenanceResolver`)** :
   - Capacité de reconstituer automatiquement une `ReplayRequest` à partir d'un identifiant de version (`dataset_id` + `version_id`) ou d'un `run_id`.
   - Restauration fidèle de l'`IngestionDefinition` et localisation de l'artefact RAW historique source sans intervention manuelle.
2. **Modélisation de la Lignée de Replay (`ReplayLineage`)** :
   - Enregistrement immuable liant `source_run_id` ➔ `replay_run_id` avec les empreintes de hachage SHA-256 respectives et le statut de concordance `matched: bool`.
3. **Persistance Durable de la Lignée dans `PublicationLedger`** :
   - Extension du port `PublicationLedger` et implémentations dans `MemoryPublicationLedger` et `PostgresPublicationLedger` (`pyingestkit_v2_replay_lineage`).
4. **Publication Conditionnelle Gouvernée Post-Replay** :
   - Passerelle explicite vers `ConditionalDatasetPublisher` (CAS) pour publier de façon atomique la version rejouée lorsqu'elle est validée.
5. **Modernisation de la CLI `pik replay`** :
   - Migration de la commande `pik replay` vers le moteur V2 avec support des options `--publish`, `--json` et rendu enrichi avec `rich`.

### Hors Périmètre (Exclusions Délibérées)
- Pas de réacquisition réseau ou modification du connecteur source : le replay opère à 100 % sur les données RAW capturées.
- Pas de modification de l'API racine gelée (`src/pyingestkit/__init__.py`) : exposition via les namespaces qualifiés `pyingestkit.replay` et `pyingestkit.governance`.

---

## 2. Diagramme d'Architecture & Flux de Données

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| FLUX D'EXÉCUTION DU REPLAY GOUVERNÉ ET DE RECONSTRUCTION HISTORIQUE                              |
|                                                                                                   |
|  [ IngestionRunId / DatasetVersionReference ]                                                     |
|                         │                                                                         |
|                         ▼                                                                         |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | ReplayProvenanceResolver                                                                    |  |
|  | - Recherche dans ArtifactStore & DatasetVersionStore                                        |  |
|  | - Restauration de l'IngestionDefinition d'origine                                           |  |
|  | - Redaction des paramètres de credentials                                                  |  |
|  | - Production d'une ReplayRequest validée                                                    |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                         │                                                                         |
|                         ▼                                                                         |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | ReplayServiceV2                                                                             |  |
|  | - Allocation d'un nouvel IngestionRunId (replay_run_id != source_run_id)                     |  |
|  | - Matérialisation de l'artefact RAW de replay avec vérification SHA-256                      |  |
|  | - Décodage & Validation via IngestionRuntime (execute_from_raw)                             |  |
|  | - Évaluation du statut de conformité (matched: bool)                                        |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                         │                                                                         |
|                         ▼                                                                         |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | PublicationLedger (Memory / PostgreSQL)                                                     |  |
|  | - Enregistrement de ReplayLineage (source_run_id -> replay_run_id, empreintes, horodatage)     |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|                         │                                                                         |
|                         ▼ (Optionnel si --publish / publish=True)                                 |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | ConditionalDatasetPublisher                                                                 |  |
|  | - Publication CAS atomique de la version qualifiée                                          |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
src/pyingestkit/
├── domain/
│   └── replay/
│       ├── __init__.py                     # [MODIFICATION] Export de ReplayLineage
│       └── models.py                       # [MODIFICATION] ReplayLineage, ReplayRequest extensions
├── ports/
│   ├── governance.py                       # [MODIFICATION] Méthodes record_replay_lineage & list_replays
│   └── replay.py                           # [CRÉATION] Port ReplayProvenanceResolver
├── application/
│   ├── replay.py                           # [MODIFICATION] Support lineage et ledger dans ReplayServiceV2
│   └── resolver.py                         # [CRÉATION] Implémentation du ReplayProvenanceResolver
├── governance/
│   └── _ledger_codec.py                    # [MODIFICATION] Sérialisation / désérialisation de ReplayLineage
├── adapters/
│   ├── memory/
│   │   └── publication_ledger.py           # [MODIFICATION] Stockage de la lignée de replay en mémoire
│   └── postgres/
│       └── publication_ledger.py           # [MODIFICATION] Table pyingestkit_v2_replay_lineage & requêtes SQL
├── replay/
│   └── v2.py                               # [MODIFICATION] Export du resolver et de ReplayLineage
└── cli/
    └── commands/
        └── replay.py                       # [MODIFICATION] Refonte V2 de la commande pik replay

tests/
├── unit/v2/
│   └── test_replay_provenance_v2.py        # [CRÉATION] Tests unitaires du resolver et de la lignée
├── conformance/v2/
│   └── test_ledger_replay_conformance.py   # [CRÉATION] Tests de conformité Memory & PostgreSQL pour la lignée
└── integration/v2/
    └── test_postgres_replay_lineage.py     # [CRÉATION] Tests d'intégration E2E du replay avec PostgreSQL

docs/
└── guides/
    └── historical-replay-and-provenance.md # [CRÉATION] Guide utilisateur complet pour le replay V2
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Domaine Replay & Modèles de Lignée
**Fichier à modifier :** `src/pyingestkit/domain/replay/models.py`

1. Créer la dataclass `ReplayLineage` :
   - `lineage_id`: `str` (UUID v4)
   - `source_run_id`: `IngestionRunId`
   - `replay_run_id`: `IngestionRunId`
   - `dataset_id`: `str`
   - `version_id`: `str`
   - `origin_raw_checksum`: `str`
   - `replay_raw_checksum`: `str`
   - `matched`: `bool`
   - `replayed_at`: `datetime` (fuseau horaire obligatoire)
   - `published`: `bool`
2. Mettre à jour `ReplayResult` pour inclure optionnellement `lineage: ReplayLineage | None = None`.

---

### Phase 2 — Service de Résolution de Provenance
**Fichiers à créer :**
- `src/pyingestkit/ports/replay.py` : Protocol `ReplayProvenanceResolver`.
- `src/pyingestkit/application/resolver.py` : Implémentation `DefaultReplayProvenanceResolver`.

Fonctionnalités :
- `resolve_from_version(dataset_id: str, version_id: str) -> ReplayRequest`
- `resolve_from_run(source_run_id: IngestionRunId) -> ReplayRequest`
- Masquage des variables sensibles dans l'`IngestionDefinition` restaurée.

---

### Phase 3 — Persistance de la Lignée dans `PublicationLedger`
**Fichiers à modifier :**
- `src/pyingestkit/ports/governance.py` :
  - `record_replay_lineage(self, lineage: ReplayLineage) -> ReplayLineage: ...`
  - `list_replays(self, dataset_id: str | None = None, source_run_id: IngestionRunId | None = None) -> tuple[ReplayLineage, ...]: ...`
- `src/pyingestkit/adapters/memory/publication_ledger.py` :
  - Gestion thread-safe d'une liste `_replays: list[ReplayLineage]`.
- `src/pyingestkit/adapters/postgres/publication_ledger.py` :
  - Déclaration de la table `_REPLAY_LINEAGE` dans `_METADATA` :
    ```python
    _REPLAY_LINEAGE = Table(
        "pyingestkit_v2_replay_lineage",
        _METADATA,
        Column("lineage_id", String(36), primary_key=True),
        Column("source_run_id", String(36), nullable=False, index=True),
        Column("replay_run_id", String(36), nullable=False, unique=True, index=True),
        Column("dataset_id", String(512), nullable=False, index=True),
        Column("version_id", String(512), nullable=False),
        Column("origin_raw_checksum", String(64), nullable=False),
        Column("replay_raw_checksum", String(64), nullable=False),
        Column("matched", Boolean, nullable=False),
        Column("replayed_at", DateTime(timezone=True), nullable=False),
        Column("published", Boolean, nullable=False, default=False),
    )
    ```

---

### Phase 4 — Intégration Replay & Publication Conditionnelle
**Fichier à modifier :** `src/pyingestkit/application/replay.py`

1. Permettre l'injection optionnelle d'un `PublicationLedger` dans `ReplayServiceV2`.
2. Si le ledger est présent, enregistrer automatiquement la `ReplayLineage` générée.
3. Ajouter une méthode explicite `publish_replay(replay_result, conditional_publisher, ...)` assurant la publication CAS conditionnelle.

---

### Phase 5 — Modernisation de la CLI `pik replay`
**Fichier à modifier :** `src/pyingestkit/cli/commands/replay.py`

- Support des arguments :
  `pik replay <run_id_or_version_id> [--publish] [--param key=value] [--json]`
- Résolution dynamique via `ReplayProvenanceResolver`.
- Affichage clair du statut de concordance et de l'identifiant du nouveau run.

---

### Phase 6 — Qualification & Validation

Commandes de vérification :
```bash
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```

---

## 5. Critères d'Acceptation & Validation

- [ ] `ReplayLineage` est modélisé et immuable.
- [ ] `ReplayProvenanceResolver` résout une `ReplayRequest` valide à partir d'un `version_id`.
- [ ] `MemoryPublicationLedger` et `PostgresPublicationLedger` enregistrent et listent les lignées de replay sans altérer les transactions de publication existantes.
- [ ] `ReplayServiceV2` enregistre la lignée et garantit `replay_run_id != source_run_id` et l'intégrité SHA-256.
- [ ] La CLI `pik replay` fonctionne en mode interactif et en mode `--json`.
- [ ] La suite de tests passe à 100 % et les 11 symboles de l'API racine restent strictement préservés.
