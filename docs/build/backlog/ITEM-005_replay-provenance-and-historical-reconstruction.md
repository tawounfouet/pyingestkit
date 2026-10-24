# ITEM-005 : Provenance Replay & Reconstruction Historique d'Ingestion

- **Statut :** ACCEPTED
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** HAUTE
- **Composant Cible :** Core Domain / Replay Engine (`src/pyingestkit/domain/replay/`)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../../roadmap/post-2.0-scope-review.md) (Section 3.2)
- **LOT Cible :** LOT-35 (v2.2.0)

---

## 1. Contexte & Problématique Constatée

Le replay strict a été introduit au jalon LOT-11, mais plusieurs capacités avancées de gouvernance d'historique sont restées en suspens post-2.0 :
1. Recherche automatique des métadonnées du run source à partir de l'identifiant de dataset versionné.
2. Restauration fidèle de l'objet `IngestionDefinition` d'origine.
3. Persistance de la lignée de replay (*replay lineage*) dans le ledger SQL (relation parent-run ➔ child-replay-run).
4. Publication conditionnelle explicite à l'issue d'un replay qualifié.

---

## 2. Expression du Besoin & User Story

- **En tant que :** Data Engineer ou auditeur de conformité réglementaire.
- **Je souhaite :** Pouvoir rejouer fidèlement un run d'ingestion historique à partir de son empreinte RAW, en enregistrant explicitement la traçabilité de cette ré-exécution dans le ledger.
- **Afin de :** Garantir la reproductibilité déterministe des calculs sans altérer l'intégrité de l'historique d'acquisition original.

---

## 3. Bénéfices Attendus

1. **Reproductibilité :** Reconstruction exacte sans solliciter à nouveau le fournisseur externe (S3, API HTTP, Base source).
2. **Lignée d'audit :** Graphe orienté clair entre le run initial défaillant et le run de replay correctif.
3. **Sécurité :** Redaction automatique des overrides de paramètres secrets lors de la restauration.

---

## 4. Invariants Non-Négociables

```text
1. replay != live reacquisition (zéro appel au fournisseur amont)
2. new replay run id != source run id (le run id de replay est strictement unique)
3. exact RAW integrity evidence is mandatory (vérification de hachage SHA-256 obligatoire)
4. publication after replay is explicit (pas de publication automatique aveugle)
```

---

## 5. Prochaine Étape

Rédiger l'analyse d'architecture dans `docs/analyses/` et soumettre le plan d'implémentation pour le jalon v2.2.0.
