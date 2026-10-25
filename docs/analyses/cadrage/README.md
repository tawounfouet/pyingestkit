# Dossier de Cadrage Préalable : `docs/analyses/cadrage/`

Ce répertoire regroupe les **notes d'exploration technique et de cadrage préliminaire** de PyIngestKit.

---

## 1. Rôle dans le Cycle de Développement

Avant d'engager la rédaction d'une analyse d'architecture exhaustive (dans `docs/analyses/`) et d'un plan d'implémentation détaillé (dans `docs/build/plans/`), chaque nouveau lot ou chantier significatif fait l'objet d'un **cadrage préalable**.

```text
[ Item Backlog / Roadmap ]
            │
            ▼
┌────────────────────────────────────────────────────────┐
│ 1. Cadrage Préalable (docs/analyses/cadrage/)          │
│    - Contexte succinct & problématique terrain         │
│    - Schéma d'architecture préliminaire (Mermaid)      │
│    - Identification des invariants & garde-fous        │
│    - Découpage en phases & questions d'arbitrage       │
└────────────────────────────────────────────────────────┘
            │  (Validation Utilisateur / Pair Programming)
            ▼
┌────────────────────────────────────────────────────────┐
│ 2. Analyse Approfondie (docs/analyses/)                │
│    - Benchmark, comparatifs, spécifications formelles  │
└────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────┐
│ 3. Plan d'Implémentation (docs/build/plans/)           │
│    - Cartographie des fichiers, contrats détaillés     │
└────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────┐
│ 4. Tâches Opérationnelles (docs/build/tasks/ & TODOS)  │
│    - Découpage unitaire & exécution                    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Conventions de Nommage

Chaque note de cadrage est nommée selon le standard :
```text
YYYY-MM-DD_cadrage-lot<NUMERO>-<nom-du-lot>.md
```

*Exemple :* `2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md`

---

## 3. Structure Type d'une Note de Cadrage

Le modèle de référence pour rédiger une nouvelle note de cadrage est disponible dans [`TEMPLATE_CADRAGE.md`](./TEMPLATE_CADRAGE.md) :

1. **En-tête métadonnées :** Date, Auteur, Item Backlog, LOT Cible, Statut, Documents aval.
2. **Contexte & Problématique Actuelle :** Ce qui manque ou pose problème en production.
3. **Architecture Cible Proposée :** Diagramme Mermaid **et** son équivalent ASCII obligatoire.
4. **Garde-fous & Invariants :** Isolation hexagonale, API publique gelée, sécurité, etc.
5. **Découpage du Lot Prévu :** Tableau des livrables et fichiers impactés.
6. **Points de Cadrage & Décisions :** Questions soumises à arbitrage avant conception détaillée.

---

## 4. Index des Notes de Cadrage

| Date | Fichier | LOT | Intitulé | Statut |
| :--- | :--- | :---: | :--- | :---: |
| 2026-10-25 | [`2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md`](./2026-10-25_cadrage-lot36-postgres-upsert-merge-and-staging.md) | LOT-36 | Adaptateur PostgreSQL UPSERT/MERGE et Staging Transactionnel | ✅ VALIDÉ |
| 2026-10-25 | [`2026-10-25_cadrage-lot37-advanced-http-acquisition-and-ssrf-hardening.md`](./2026-10-25_cadrage-lot37-advanced-http-acquisition-and-ssrf-hardening.md) | LOT-37 | Acquisition HTTP Avancée, Rafraîchissement OAuth & Durcissement SSRF | 💡 PROPOSÉ |
