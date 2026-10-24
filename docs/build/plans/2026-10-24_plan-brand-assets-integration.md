# Plan d'Implémentation : Intégration Globale de la Marque & Design System PyIngestKit

- **Projet** : PyIngestKit
- **Statut** : Prêt pour implémentation
- **Date** : 24 Octobre 2026
- **Auteur** : Antigravity / Pair Programming
- **Document source** : [`../../analyses/2026-10-24_brand-assets-and-package-integration-analysis.md`](../../analyses/2026-10-24_brand-assets-and-package-integration-analysis.md)
- **Pack d'assets amont** : [`../../../resources/pyingestkit-brand-assets-v1`](../../../resources/pyingestkit-brand-assets-v1)
- **Branche cible** : `feat/brand-identity-and-docs-integration`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation opérationnel a pour but d'intégrer de façon native et standardisée le kit d'identité visuelle officielle ([`pyingestkit-brand-assets-v1`](../../../resources/pyingestkit-brand-assets-v1)) dans le framework **PyIngestKit** :

1. **Provisioning des assets** : Importation sélective et structurée des visuels dans [`docs/assets/`](../../../docs) (logos, marques PIK, favicons, cartes OpenGraph, manifest).
2. **Design Tokens & Thème MkDocs** : Mise en œuvre des variables CSS officielles (`--pyingestkit-*`) et personnalisation du thème Material for MkDocs en mode sombre et clair.
3. **Hero Adaptatif GitHub (`README.md`)** : Intégration d'un en-tête graphique dynamique commutant automatiquement entre fond sombre et fond clair grâce à la balise `<picture>`.
4. **Vitrine Documentation (`docs/index.md`)** : Mise à niveau visuelle de la page d'accueil de la documentation en ligne avec le logo horizontal et les signatures certifiées.
5. **Favicons & PWA** : Intégration du favicon multi-résolution `.ico`, des icônes tactiles Apple/Android et de `site.webmanifest`.
6. **Validation Stricte** : Vérification du build documentaire (`mkdocs build --strict`) sans avertissement de lien ou d'asset manquant.

---

## 2. Diagramme d'Architecture de l'Intégration Visuelle

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| ARCHITECTURE DE L'INTÉGRATION DE LA MARQUE PYINGESTKIT                                           |
|                                                                                                   |
|  [ Source : resources/pyingestkit-brand-assets-v1 ]                                               |
|                           │                                                                       |
|                           ▼                                                                       |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | Copie dans : pyingestkit/docs/assets/                                                       |  |
|  |                                                                                             |  |
|  |  ├── brand/     : Logos (horizontal, vertical), lockups dark/light, marks couleur & dark    |  |
|  |  ├── favicons/  : favicon.ico, 16x16, 32x32, apple-touch, android-chrome, site.webmanifest  |  |
|  |  ├── social/    : pyingestkit-og-dark-1200x630.jpg, pyingestkit-og-light-1200x630.jpg       |  |
|  |  └── tokens/    : pyingestkit-brand-tokens.css (:root CSS variables)                       |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|             │                                                  │                                  |
|             ▼                                                  ▼                                  |
|  +──────────────────────────────+           +──────────────────────────────────────────────────+  |
|  | README.md (GitHub & PyPI)    |           | mkdocs.yml (Site officiel GitHub Pages)          |  |
|  |                              |           |                                                  |  |
|  |  <picture>                   |           |  theme.logo    : mark couleur PIK                |  |
|  |   - dark  : lockup-dark.png  |           |  theme.favicon : favicons/favicon.ico            |  |
|  |   - light : lockup-light.png |           |  theme.palette : Slate (dark) / Default (light)  |  |
|  |  </picture>                  |           |  extra_css     : tokens.css + brand.css          |  |
|  |                              |           |  social_card   : pyingestkit-og-dark-1200x630.jpg|  |
|  |  Taglines officielles        |           +──────────────────────────────────────────────────+  |
|  +──────────────────────────────+                                      │                          |
|                                                                        ▼                          |
|                                             +──────────────────────────────────────────────────+  |
|                                             | docs/index.md & Documentation                    |  |
|                                             | - Logo horizontal principal                      |  |
|                                             | - Promesse : "From any source to reliable..."    |  |
|                                             | - Cycle : Acquire -> Process -> Validate -> Pub  |  |
|                                             +──────────────────────────────────────────────────+  |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
docs/
├── assets/
│   ├── brand/
│   │   ├── pyingestkit-logo-horizontal.png             # [IMPORT] Logo officiel principal
│   │   ├── pyingestkit-logo-horizontal@2x.png          # [IMPORT] Logo Retina High-DPI
│   │   ├── pyingestkit-primary-lockup-dark.png         # [IMPORT] Hero lockup pour surfaces sombres
│   │   ├── pyingestkit-primary-lockup-light.png        # [IMPORT] Hero lockup pour surfaces claires
│   │   ├── pyingestkit-pik-mark-color.png              # [IMPORT] Pictogramme PIK pour nav bar MkDocs
│   │   ├── pyingestkit-pik-mark-color@2x.png           # [IMPORT] Pictogramme PIK Retina
│   │   └── pyingestkit-pik-icon-dark.png               # [IMPORT] Icône carrée fond sombre
│   ├── favicons/
│   │   ├── favicon.ico                                 # [IMPORT] Favicon multi-résolution navigateur
│   │   ├── favicon-16x16.png                           # [IMPORT] Favicon petit format
│   │   ├── favicon-32x32.png                           # [IMPORT] Favicon format standard
│   │   ├── apple-touch-icon.png                        # [IMPORT] Icône iOS
│   │   ├── android-chrome-192x192.png                  # [IMPORT] Icône PWA
│   │   ├── android-chrome-512x512.png                  # [IMPORT] Splash screen PWA
│   │   └── site.webmanifest                            # [IMPORT] Manifeste web officiel
│   ├── social/
│   │   ├── pyingestkit-og-dark-1200x630.jpg            # [IMPORT] OpenGraph preview dark
│   │   └── pyingestkit-og-light-1200x630.jpg           # [IMPORT] OpenGraph preview light
│   └── pyingestkit-brand-tokens.css                    # [IMPORT] Variables CSS certifiées
├── stylesheets/
│   └── brand.css                                       # [CRÉATION] Styles MkDocs Material & Hero
├── index.md                                            # [MODIFICATION] Intégration du bandeau & signatures
README.md                                               # [MODIFICATION] En-tête <picture> adaptatif
mkdocs.yml                                              # [MODIFICATION] Configuration logo, favicon, palette
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Provisioning des Assets Graphiques
**Objectif :** Copier les fichiers du kit officiel en créant les répertoires cibles dans `docs/assets/`.

```bash
# Arborescence cible
mkdir -p docs/assets/brand docs/assets/favicons docs/assets/social docs/stylesheets

# 1. Logos & Marks
cp ../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-logo-horizontal.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-logo-horizontal@2x.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-primary-lockup-dark.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-primary-lockup-light.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/mark/pyingestkit-pik-mark-color.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/mark/pyingestkit-pik-mark-color@2x.png docs/assets/brand/
cp ../../../resources/pyingestkit-brand-assets-v1/mark/pyingestkit-pik-icon-dark.png docs/assets/brand/

# 2. Favicons & Manifest
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/favicon.ico docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/favicon-16x16.png docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/favicon-32x32.png docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/apple-touch-icon.png docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/android-chrome-192x192.png docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/favicon/android-chrome-512x512.png docs/assets/favicons/
cp ../../../resources/pyingestkit-brand-assets-v1/web/site.webmanifest docs/assets/favicons/

# 3. Social OpenGraph
cp ../../../resources/pyingestkit-brand-assets-v1/social/pyingestkit-og-dark-1200x630.jpg docs/assets/social/
cp ../../../resources/pyingestkit-brand-assets-v1/social/pyingestkit-og-light-1200x630.jpg docs/assets/social/

# 4. Design Tokens CSS
cp ../../../resources/pyingestkit-brand-assets-v1/web/pyingestkit-brand-tokens.css docs/assets/
```

---

### Phase 2 — Feuilles de Style du Thème (`docs/stylesheets/brand.css`)
**Fichier à créer :** [`docs/stylesheets/brand.css`](../../../docs/stylesheets/brand.css)

Ce fichier connecte les tokens de marque aux hooks du thème Material for MkDocs :

```css
/* Intégration de la charte graphique officielle PyIngestKit */

:root {
  --md-primary-fg-color:        #0B2447; /* Navy */
  --md-primary-fg-color--light: #2563EB; /* Blue */
  --md-primary-fg-color--dark:  #07172E;
  --md-accent-fg-color:         #06B6D4; /* Cyan */
}

/* Ajustement pour le thème sombre (slate) */
[data-md-color-scheme="slate"] {
  --md-primary-fg-color:        #0B2447;
  --md-primary-fg-color--light: #2563EB;
  --md-primary-fg-color--dark:  #040D1A;
  --md-accent-fg-color:         #06B6D4;
}

/* En-tête de page Hero personnalisée */
.pik-hero {
  text-align: center;
  padding: 2.5rem 1rem 1.5rem;
}

.pik-hero img {
  max-width: 480px;
  width: 100%;
  height: auto;
  margin-bottom: 1rem;
}

.pik-hero .pik-tagline {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--pyingestkit-blue);
  margin-bottom: 0.5rem;
}

.pik-hero .pik-lifecycle {
  font-size: 0.95rem;
  color: var(--md-default-fg-color--light);
  letter-spacing: 0.05em;
  font-family: monospace;
}
```

---

### Phase 3 — Configuration MkDocs (`mkdocs.yml`)
**Fichier à modifier :** [`mkdocs.yml`](../../../mkdocs.yml)

Mise à jour des blocs `site_description`, `theme`, `extra_css` et `extra` :

```yaml
site_name: PyIngestKit
site_description: From any source to reliable datasets. Composable batch ingestion and governance for Python.
site_url: https://tawounfouet.github.io/pyingestkit/
repo_url: https://github.com/tawounfouet/pyingestkit
repo_name: tawounfouet/pyingestkit
edit_uri: edit/main/docs/

theme:
  name: material
  language: en
  logo: assets/brand/pyingestkit-pik-mark-color.png
  favicon: assets/favicons/favicon.ico
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.action.edit
  palette:
    # 1. Mode Clair automatique ou sélectionné
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: custom
      accent: blue
      toggle:
        icon: material/brightness-7
        name: Passer au mode sombre
    # 2. Mode Sombre automatique ou sélectionné
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: custom
      accent: cyan
      toggle:
        icon: material/brightness-4
        name: Passer au mode clair

extra_css:
  - assets/pyingestkit-brand-tokens.css
  - stylesheets/brand.css

extra:
  version:
    provider: mike
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/tawounfouet/pyingestkit
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/pyingestkit/
```

---

### Phase 4 — Hero Adaptatif GitHub dans `README.md`
**Fichier à modifier :** [`README.md`](../../../README.md)

Remplacement des lignes d'en-tête (lignes 1 à 12) par une présentation visuelle soignée :

```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/pyingestkit-primary-lockup-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/pyingestkit-primary-lockup-light.png">
    <img src="docs/assets/brand/pyingestkit-logo-horizontal.png" alt="PyIngestKit — From any source to reliable datasets" width="480">
  </picture>
</p>

<p align="center">
  <strong>From any source to reliable datasets.</strong><br>
  <code>Acquire</code> &nbsp;→&nbsp; <code>Process</code> &nbsp;→&nbsp; <code>Validate</code> &nbsp;→&nbsp; <code>Publish</code>
</p>

<p align="center">
  <a href="https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml"><img src="https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml"><img src="https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg" alt="Security"></a>
  <a href="https://pypi.org/project/pyingestkit/"><img src="https://img.shields.io/pypi/v/pyingestkit.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg" alt="Python 3.11–3.14"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="docs/releases/v2.1.0.md"><img src="https://img.shields.io/badge/stable-2.1.0-brightgreen.svg" alt="Stable: 2.1.0"></a>
  <a href="https://tawounfouet.github.io/pyingestkit/"><img src="https://img.shields.io/badge/docs-online-blue.svg" alt="Docs"></a>
</p>

---

**PyIngestKit** is a focused Python framework for reliable, traceable and replayable batch ingestion.
```

---

### Phase 5 — Page d'Accueil de la Documentation (`docs/index.md`)
**Fichier à modifier :** [`docs/index.md`](../../../docs/index.md)

Ajout du composant Hero et mise en valeur de la promesse de marque :

```markdown
# PyIngestKit

<p align="center">
  <img src="assets/brand/pyingestkit-logo-horizontal.png" alt="PyIngestKit logo" width="460">
</p>

<p align="center">
  <strong>From any source to reliable datasets.</strong><br>
  <code>Acquire</code> &nbsp;→&nbsp; <code>Process</code> &nbsp;→&nbsp; <code>Validate</code> &nbsp;→&nbsp; <code>Publish</code>
</p>

---

## Welcome to PyIngestKit

PyIngestKit is a focused Python framework for reliable, traceable and replayable batch ingestion.
```

---

## 5. Matrice de Risques & Contrôles

| Risque identifié | Probabilité | Impact | Mesure de mitigation |
| :--- | :--- | :--- | :--- |
| **Image cassée en mode sombre GitHub** | Faible | Moyen | Utilisation de la syntaxe officielle GitHub `<picture>` testée |
| **Erreur de build MkDocs (asset non trouvé)** | Faible | Élevé | Validation via `make docs-build` (`mkdocs build --strict`) |
| **Poids excessif des assets dans le repository Git** | Très faible | Faible | Le pack totalise moins de 3 Mo (fichiers PNG optimisés & WebP) |
| **Régression de contraste sur thèmes alternatifs** | Très faible | Faible | Variables CSS isolées dans `data-md-color-scheme` |

---

## 6. Critères d'Acceptation & Validation

- [ ] L'arborescence `docs/assets/brand/`, `docs/assets/favicons/` et `docs/assets/social/` est provisionnée et propre.
- [ ] Le fichier `docs/stylesheets/brand.css` compile sans erreur.
- [ ] La commande `make docs-build` s'exécute avec succès en mode strict (`--strict`).
- [ ] Le favicon apparaît correctement dans l'onglet du navigateur (`make docs-serve`).
- [ ] Le sélecteur de thème MkDocs (lune / soleil) bascule harmonieusement entre le thème sombre Slate et le thème clair Default.
- [ ] Le `README.md` affiche le hero adaptatif et tous les badges alignés au centre.
- [ ] La suite de tests globale `make test-v2` reste 100% verte.
