# TASK-LOT35-01 : Provenance Replay & Reconstruction Historique d'Ingestion

- **Statut :** ✅ DONE
- **Plan Parent :** [`docs/build/plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md`](../plans/2026-10-25_plan-replay-provenance-and-historical-reconstruction.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md`](../backlog/ITEM-005_replay-provenance-and-historical-reconstruction.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-25
- **Date d'achèvement :** 2026-10-25
- **Branche Git :** `feat/replay-provenance-and-historical-reconstruction`

---

## 1. Contexte & Objectif Unitaire

Implémenter l'infrastructure de traçabilité, de reconstruction historique et de replay gouverné pour PyIngestKit (LOT-35) :
1. Modéliser `ReplayLineage` pour relier le run source au run de replay avec intégrité SHA-256.
2. Créer le port et service `ReplayProvenanceResolver` pour automatiser la résolution de `ReplayRequest` depuis un identifiant de version (`version_id`) ou un run source.
3. Étendre le `PublicationLedger` (en mémoire et PostgreSQL) pour persister et requêter la lignée de replay.
4. Intégrer la publication CAS conditionnelle post-replay dans `ReplayServiceV2`.
5. Moderniser la commande CLI `pik replay` pour utiliser le moteur V2.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/domain/replay/models.py` | Modification | Ajout de `ReplayLineage` et extension de `ReplayResult` |
| `src/pyingestkit/domain/replay/__init__.py` | Modification | Export de `ReplayLineage` |
| `src/pyingestkit/ports/replay.py` | Création | Port `ReplayProvenanceResolver` |
| `src/pyingestkit/application/resolver.py` | Création | Service `DefaultReplayProvenanceResolver` |
| `src/pyingestkit/ports/governance.py` | Modification | Méthodes `record_replay_lineage` et `list_replays` |
| `src/pyingestkit/governance/_ledger_codec.py` | Modification | Codec pour la sérialisation de `ReplayLineage` |
| `src/pyingestkit/adapters/memory/publication_ledger.py` | Modification | Persistance de la lignée en mémoire |
| `src/pyingestkit/adapters/postgres/publication_ledger.py` | Modification | Table `pyingestkit_v2_replay_lineage` et requêtes SQL |
| `src/pyingestkit/application/replay.py` | Modification | Enregistrement de la lignée et publication conditionnelle |
| `src/pyingestkit/replay/v2.py` | Modification | Export des nouveaux symboles V2 |
| `src/pyingestkit/cli/commands/replay.py` | Modification | Refonte V2 de la commande `pik replay` |
| `tests/unit/v2/test_replay_provenance_v2.py` | Création | Tests unitaires du resolver et de la lignée |
| `tests/conformance/v2/test_ledger_replay_conformance.py` | Création | Tests de conformité des ledgers pour la lignée |
| `tests/integration/v2/test_postgres_replay_lineage.py` | Création | Tests d'intégration PostgreSQL pour la lignée |
| `docs/build/tasks/TODOS.md` | Modification | Mise à jour du registre des tâches |

---

## 3. Checklist d'Exécution

- [x] **Étape 1 :** Modéliser `ReplayLineage` dans `src/pyingestkit/domain/replay/models.py` et l'exporter.
- [x] **Étape 2 :** Créer les ports et services `ReplayProvenanceResolver` et `ReplayLineageLedger` dans `src/pyingestkit/ports/replay.py` et `src/pyingestkit/application/resolver.py`.
- [x] **Étape 3 :** Implémenter `ReplayLineageLedger` dans memory et postgres avec table `pyingestkit_v2_replay_lineage`.
- [x] **Étape 4 :** Mettre à jour `ReplayServiceV2` pour enregistrer la lignée et proposer la publication CAS (`publish_replay`).
- [x] **Étape 5 :** Moderniser la commande CLI `pik replay` avec support V2 (`--dataset`, `--version`, `--publish`, `--json`).
- [x] **Étape 6 :** Valider par tests unitaires, conformité et intégration (`make quality`, `make architecture-v2`, `make test-v2`, `mkdocs build --strict`).
- [x] **Étape 7 :** Rédiger la fiche REX `FEEDBACK-LOT35-01` et la revue formelle de clôture de lot.

---

## 4. Preuves & Commandes de Validation

```bash
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```

---

## 5. Résultat & Clôture de Tâche

- **Statut final :** ✅ DONE
- **Commit / PR :** [PR #71](https://github.com/tawounfouet/pyingestkit/pull/71) (merge commit: `4019da9`)
- **Fiche REX associée :** `docs/build/feedback/FEEDBACK-LOT35-01_replay-provenance-and-historical-reconstruction.md`
- **Revue de lot associée :** `docs/build/reviews/2026-10-25_lot35_replay-provenance-and-historical-reconstruction-review.md`
