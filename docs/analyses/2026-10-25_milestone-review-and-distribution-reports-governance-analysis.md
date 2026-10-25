# Analyse Technique & Gouvernance : Bilans de Milestone et Qualification de Distribution

- **Date :** 2026-10-25
- **Auteur :** Antigravity / AWF
- **Contexte :** Consolidation du cycle SDLC post-release v2.2.0 et gouvernance documentaire des artefacts de clôture
- **Références amont :**  
  - [`../build/README.md`](../build/README.md)  
  - [`../build/reviews/README.md`](../build/reviews/README.md)  
  - [`../build/reports/tests/README.md`](../build/reports/tests/README.md)  
  - [`2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md`](./2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md)

---

## 1. Contexte & Problématique

Lors de la livraison officielle de la version stable `v2.2.0` de `PyIngestKit`, scellant sept jalons de développement consécutifs (LOT-31 à LOT-37), deux constats structurants ont émergé concernant le cycle SDLC :

1. **Absence d'un espace dédié aux preuves de distribution :**  
   Le dossier `docs/build/reports/tests/` certifie la conformité logique du code source (tests unitaires, d'intégration et d'architecture), mais il n'existait pas de répertoire dédié pour formaliser et tracer les **procès-verbaux de packaging, d'intégrité supply chain et de publication PyPI** (empreintes SHA256, validation `twine check`, SBOM CycloneDX, attestations Sigstore / SLSA, test consommateur public isolé).
2. **Besoin d'un niveau macroscopique de bilan de fin de milestone :**  
   Les revues hébergées dans [`docs/build/reviews/`](../build/reviews/) clôturent aujourd'hui des **lots techniques individuels** (ex. `2026-10-24_lot31_cli-pik-standardization-review.md`, `2026-10-25_lot36_postgres-upsert-merge-and-staging-review.md`). Cependant, une **milestone** (v2.1.0, v2.2.0, v2.3.0) agrège une pluralité de lots, des arbitrages stratégiques, une évolution globale des métriques (taille du package, nombre de tests, couverture), ainsi qu'une rétrospective d'équipe et des orientations pour le cycle suivant.

La question centrale est : **comment structurer de manière pérenne et ergonomique les rapports de distribution d'une part, et les bilans de fin de milestone d'autre part, sans dénaturer le continuum SDLC ?**

---

## 2. Benchmark Comparatif des Approches

| Dimension | Approche Actuelle (Avant Analyse) | Approche avec `reports/dist` & `reviews/milestones` (Cible) | Bénéfice Opérationnel |
| :--- | :--- | :--- | :--- |
| **Preuves de Packaging** | Éparpillées dans les tâches et logs CI | Consolidées dans `docs/build/reports/dist/` | Auditabilité immédiate des distributions publiées |
| **Clôture de Chantier (Lot)** | `docs/build/reviews/lotXX_review.md` | `docs/build/reviews/lots/` (ou racine `reviews/`) | Traçabilité unitaire chirurgicale (*blast radius*) |
| **Clôture de Release (Milestone)** | Absence de bilan consolidé | `docs/build/reviews/milestones/` | Vision stratégique, vélocité globale et orientations v+1 |
| **Conformité SDLC** | 6 étapes canoniques | 6 étapes canoniques préservées | Zéro prolifération anarchique de dossiers racines |

---

## 3. Analyse Détaillée des Options Architecturales pour les Bilans de Milestone

Trois options de positionnement ont été évaluées pour accueillir les documents de bilan de milestone :

### Option 1 : `docs/build/reviews/milestones/` (Option Recommandée & Validée)
- **Principe :** Structurer l'étape 6 du SDLC (« Clôture & Revues ») en deux sous-niveaux :
  - `docs/build/reviews/lots/` (ou fichiers `lotXX_review.md` à la racine de `reviews/`) pour les clôtures de chantiers unitaires.
  - `docs/build/reviews/milestones/` pour les bilans de versions majeures/mineures (ex. `2026-10-25_milestone-v2.2.0_bilan-cloture.md`).
- **Avantages :**
  - **Cohérence conceptuelle :** Une milestone est la clôture macroscopique d'une version, tout comme un lot est la clôture microscopique d'un chantier. Les deux relèvent de la phase de revue formelle.
  - **Préservation du framework :** Maintient l'architecture en 6 dossiers racines sous `docs/build/` sans créer de dispersion.
  - **Clarté pour les agents IA :** L'agent sait que toute décision d'approbation et de clôture vit sous `docs/build/reviews/`.
- **Inconvénients :** Nécessite une arborescence à un sous-niveau dans `reviews/`.

### Option 2 : Dossier racine dédié `docs/build/bilans/` (ou `docs/build/milestones/`)
- **Principe :** Créer un septième répertoire de premier niveau sous `docs/build/`.
- **Avantages :** Visibilité immédiate au premier coup d'œil dans l'arborescence.
- **Inconvénients :** Dilue la règle des 6 piliers canoniques du SDLC (`backlog` ➔ `plans` ➔ `tasks` ➔ `feedback` ➔ `reports` ➔ `reviews`). Redondance potentielle entre « bilan » et « revue ».

### Option 3 : `docs/build/reports/milestones/`
- **Principe :** Traiter le bilan de milestone comme un procès-verbal de reporting global au sein de `reports/` (aux côtés de `reports/tests/` et `reports/dist/`).
- **Avantages :** Rassemble tous les documents de type procès-verbal / rapport au même endroit.
- **Inconvénients :** Confusion entre « rapport de mesures techniques » (factuel, orienté données) et « bilan de release » (stratégique, incluant rétrospective, arbitrage roadmap et signature d'approbation).

---

## 4. Modélisation de l'Architecture Cible

```text
docs/build/
├── backlog/                 # 1. Quoi faire ? (Items de backlog & dettes)
├── plans/                   # 2. Comment cadencer ? (Plans directeurs par LOT)
├── tasks/                   # 3. Actions atomiques (Fiches de tâches WBS & TODOS.md)
├── feedback/                # 4. Retours d'expérience (REX post-tâche & leçons)
├── reports/                 # 5. Procès-verbaux & Preuves factuelles
│   ├── tests/               #    - Qualification des tests unitaires, architecture, contrats
│   └── dist/                #    - Qualification distribution (wheels, tarball, SBOM, PyPI)
└── reviews/                 # 6. Audits de conformité & Clôture formelle
    ├── (lots/)              #    - Revues formelles de clôture de lots unitaires
    └── milestones/          #    - Bilans de clôture globale de fin de milestone / release
```

---

## 5. Matrice de Décision

| Paramètre d'Arbitrage | Choix Retenu | Rationale & Justification |
| :--- | :--- | :--- |
| **Dossier de Qualification Distribution** | `docs/build/reports/dist/` | Symétrie exacte avec `reports/tests/`, garantit l'archivage pérenne des empreintes cryptographiques et du test consommateur public. |
| **Emplacement des Bilans de Milestone** | `docs/build/reviews/milestones/` (Option 1) | Alignement strict avec la phase 6 de Clôture du continuum SDLC ; zéro pollution de la racine `docs/build/`. |
| **Périmètre du Bilan de Milestone** | Synthèse des lots, métriques, gouvernance, rétrospective & roadmap v+1 | Offre une vue d'ensemble exécutive et stratégique indispensable pour piloter le projet dans la durée. |
| **Nomenclature des Rapports Dist** | `YYYY-MM-DD_<version>_distribution-qualification-report.md` | Standardisation chronologique et lisible pour l'humain comme pour l'agent. |
| **Nomenclature des Bilans Milestone** | `YYYY-MM-DD_milestone-<version>_bilan-cloture.md` | Identification explicite du statut de clôture macroscopique. |

---

## 6. Plan d'Implémentation Opérationnel

1. **Formalisation de la Qualification de Distribution :**
   - [x] Créer [`docs/build/reports/dist/README.md`](../build/reports/dist/README.md).
   - [x] Créer [`docs/build/reports/dist/TEMPLATE_DIST_REPORT.md`](../build/reports/dist/TEMPLATE_DIST_REPORT.md).
   - [x] Publier le rapport inaugural [`docs/build/reports/dist/2026-10-25_v2.2.0_distribution-qualification-report.md`](../build/reports/dist/2026-10-25_v2.2.0_distribution-qualification-report.md).
   - [x] Ajuster `.gitignore` pour restreindre l'exclusion au seul répertoire racine `/dist/`.
2. **Mise en Place de l'Option 1 (Bilans de Milestone) :**
   - [ ] Créer le répertoire [`docs/build/reviews/milestones/`](../build/reviews/milestones/).
   - [ ] Rédiger le guide [`docs/build/reviews/milestones/README.md`](../build/reviews/milestones/README.md).
   - [ ] Rédiger le modèle standard [`docs/build/reviews/milestones/TEMPLATE_MILESTONE_REVIEW.md`](../build/reviews/milestones/TEMPLATE_MILESTONE_REVIEW.md).
   - [ ] Rédiger le bilan inaugural consolidé pour la version stable :  
     [`docs/build/reviews/milestones/2026-10-25_milestone-v2.2.0_bilan-cloture.md`](../build/reviews/milestones/2026-10-25_milestone-v2.2.0_bilan-cloture.md).
   - [ ] Mettre à jour [`docs/build/reviews/README.md`](../build/reviews/README.md) et [`docs/build/README.md`](../build/README.md).
