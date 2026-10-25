# Bilans de Clôture de Milestone & Releases : `docs/build/reviews/milestones/`

Ce répertoire héberge les **bilans de clôture macroscopique**, revues consolidées de release et rétrospectives stratégiques marquant l'achèvement d'une **version majeure ou mineure** de [`PyIngestKit`](../../../../README.md).

---

## 1. Rôle dans l'Étape 6 du SDLC (« Clôture & Revues »)

Tandis que les revues de lot à la racine de [`docs/build/reviews/`](../) scellent des chantiers techniques unitaires (ex. LOT-31 CLI, LOT-36 Postgres UPSERT), les bilans de ce dossier clôturent l'ensemble d'un **cycle de release (Milestone)** :
- **Consolidation multi-lots :** Synthèse exhaustive de tous les chantiers intégrés dans la version (ex. LOT-31 à LOT-37 pour la v2.2.0).
- **Indicateurs & métriques globales du cycle :** Évolution du nombre de tests (unitaires, architecture, contrats), couverture de code, volume de lignes de code et empreinte binaire.
- **Vérification d'inviolabilité contractuelle :** Garantie stricte de zéro régression et préservation de l'API publique racine (11 symboles gelés).
- **Rétrospective opérationnelle :** Succès techniques, difficultés et frictions surmontées, dettes techniques apurées.
- **Orientations pour le cycle suivant :** Identification des priorités candidates du backlog pour la future version (ex. v2.3.0).

---

## 2. Convention de Nommage des Bilans

```text
YYYY-MM-DD_milestone-<version>_bilan-cloture.md
```

### Exemple :
- `2026-10-25_milestone-v2.2.0_bilan-cloture.md`

---

## 3. Modèle Standard

Pour rédiger le bilan de clôture d'une nouvelle version, dupliquer le modèle de référence :
[`TEMPLATE_MILESTONE_REVIEW.md`](./TEMPLATE_MILESTONE_REVIEW.md).
