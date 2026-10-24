# Backlog Technique & Expression de Besoins : `docs/build/backlog/`

Ce répertoire héberge les **fiches d'expression de besoins bruts**, de dettes techniques et de propositions d'évolutions destinées à être instruites et planifiées dans [`PyIngestKit`](../../README.md).

---

## 1. Rôle dans le SDLC

Le backlog est le point d'entrée amont du cycle de vie logiciel :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| CYCLE DU BACKLOG VERS LA LIVRAISON                                                                |
|                                                                                                   |
|  1. BACKLOG                    2. ANALYSES & PLANS              3. TASKS                          |
|  ┌──────────────────────┐     ┌──────────────────────────┐     ┌────────────────────────────┐     |
|  │ docs/build/backlog/  │────>│ docs/analyses/           │────>│ docs/build/tasks/          │     |
|  │                      │     │ docs/build/plans/        │     │                            │     |
|  │ - Besoin brut cadré  │     │ - Analyse d'impact       │     │ - Tâches atomiques de dév  │     |
|  │ - Ticket de dette    │     │ - Plan directeur par LOT │     │ - WBS unitaire de session  │     |
|  └──────────────────────┘     └──────────────────────────┘     └────────────────────────────┘     |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Nomenclature des Items de Backlog

Chaque fichier de backlog respecte la convention :
```text
ITEM-<NUMERO>_<intitule-court-kebab-case>.md
```

### États d'un Item de Backlog :
- **`PROPOSED`** : Besoin initialement soumis, en attente de qualification.
- **`ACCEPTED`** : Besoin validé pour intégration dans un plan directeur.
- **`PLANNED`** : Planifié dans un plan de livraison officiel (`docs/build/plans/`).
- **`REJECTED`** : Hors périmètre ou incompatible avec les invariants gelés V2.

---

## 3. Gabarit Type d'une Fiche de Backlog

```markdown
# ITEM-<NUMERO> : <Intitulé du Besoin / Dette>

- **Statut :** PROPOSED | ACCEPTED | PLANNED | REJECTED
- **Auteur :** Antigravity / AWF
- **Date :** YYYY-MM-DD
- **Priorité :** CRITIQUE | HAUTE | MOYENNE | BASSE

## 1. Contexte & Problème Constaté
Description claire du besoin ou de la limitation actuelle.

## 2. Bénéfices Attendus
- Performance, sécurité, maintenabilité ou ergonomie.

## 3. Contraintes & Invariants
- Respect de l'architecture hexagonale et des 11 symboles de la racine.
- Zéro régression sur le ledger immuable et le CAS.

## 4. Registre Actuel des Items du Backlog

| Réf. Item | Intitulé du Besoin / Dette | Priorité | Jalon / LOT Cible | Statut | Fichier |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ITEM-001** | Standardisation CLI `pik` & Bootstrap Stdlib | HAUTE | LOT-31 (v2.1.1) | ✅ **DONE** | [`ITEM-001`](./ITEM-001_cli-pik-standardization.md) |
| **ITEM-002** | Assainissement Racine & Profils YAML | HAUTE | LOT-32 (v2.1.1) | ✅ **DONE** | [`ITEM-002`](./ITEM-002_root-cleanup-and-profile-reorganization.md) |
| **ITEM-003** | Charte Graphique & Brand Assets v1 | MOYENNE | LOT-33 (v2.1.1) | 🚀 **PLANNED** | [`ITEM-003`](./ITEM-003_brand-assets-and-visual-identity.md) |
| **ITEM-004** | Supply Chain CI/CD & PyPI OIDC | CRITIQUE | LOT-34 (v2.1.1) | 🚀 **PLANNED** | [`ITEM-004`](./ITEM-004_pypi-supply-chain-and-release-automation.md) |
| **ITEM-005** | Provenance Replay & Reconstruction Historique | HAUTE | LOT-35 (v2.2.0) | 📋 **ACCEPTED** | [`ITEM-005`](./ITEM-005_replay-provenance-and-historical-reconstruction.md) |
| **ITEM-006** | Sémantique Cible PostgreSQL (UPSERT/MERGE) | MOYENNE | LOT-36 (v2.2.0) | 💡 **PROPOSED** | [`ITEM-006`](./ITEM-006_postgresql-target-upsert-merge-and-staging.md) |
| **ITEM-007** | Acquisition HTTP Avancée & Durcissement SSRF | MOYENNE | LOT-37 (v2.3.0) | 💡 **PROPOSED** | [`ITEM-007`](./ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md) |

