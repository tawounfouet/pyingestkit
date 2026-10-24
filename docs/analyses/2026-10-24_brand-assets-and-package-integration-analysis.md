# Analyse du Brand Kit & Guide d'Intégration Globale : PyIngestKit

- **Date :** 24 Octobre 2026  
- **Auteur :** Antigravity / Pair Programming  
- **Source des assets :** [`../../../resources/pyingestkit-brand-assets-v1`](../../../resources/pyingestkit-brand-assets-v1)  
- **Cible :** Package [`PyIngestKit`](../../README.md)  
- **Document source :** [`ASSET_INVENTORY.txt`](../../../resources/pyingestkit-brand-assets-v1/ASSET_INVENTORY.txt) & [`brand/BRAND_GUIDE.md`](../../../resources/pyingestkit-brand-assets-v1/brand/BRAND_GUIDE.md)

---

## 1. Contexte & Identité de Marque

Dans le cadre de la consolidation de la ligne 2.x et de l'alignement professionnel du monorepo, un pack complet d'assets de marque officiel a été livré sous [`professionnal/webtech/packages/resources/pyingestkit-brand-assets-v1`](../../../resources/pyingestkit-brand-assets-v1).

Ce kit confère à PyIngestKit une identité visuelle d'entreprise reconnaissable, cohérente et adaptée aux supports modernes (GitHub Light/Dark, documentation MkDocs Material, PyPI, réseaux sociaux, OpenGraph et applications web).

### Signatures & Promesses Officielles

```text
+---------------------------------------------------------------------------------------------------+
| HIERARCHIE DES SIGNATURES DE MARQUE                                                               |
|                                                                                                   |
|  1. Promesse Principale (Produit / Hero) :                                                       |
|     "From any source to reliable datasets."                                                       |
|                                                                                                   |
|  2. Signature Fonctionnelle (Cycle de vie technique) :                                           |
|     "Acquire  ───>  Process  ───>  Validate  ───>  Publish"                                       |
+---------------------------------------------------------------------------------------------------+
```

### Palette de Couleurs Certifiée

| Rôle Sémantique | Token CSS | Code Hex | Signification / Emploi |
| :--- | :--- | :--- | :--- |
| **Confidence / Infrastructure** | `--pyingestkit-navy` | `#0B2447` | Couleur primaire d'ancrage, arrière-plans sombres, typographie |
| **Technical reliability** | `--pyingestkit-blue` | `#2563EB` | Accent technique, boutons primaires, liens actifs, états focus |
| **Flow / Ingestion** | `--pyingestkit-cyan` | `#06B6D4` | Flux de données entrant, acquisition, étapes actives |
| **Reliable data / Publication** | `--pyingestkit-green` | `#10B981` | Validation réussie, dataset publié, badges de statut stable |

---

## 2. Inventaire Analytique des Artefacts Livrés

Le pack est composé de 36 fichiers vérifiés par somme de contrôle SHA-256 :

```text
+---------------------------------------------------------------------------------------------------+
| ARBORESCENCE DU KIT DE MARQUE (pyingestkit-brand-assets-v1)                                       |
|                                                                                                   |
|  pyingestkit-brand-assets-v1/                                                                     |
|  ├── brand/                                                                                       |
|  │   ├── BRAND_GUIDE.md                          <- Charte d'utilisation et règles                |
|  │   └── pyingestkit-approved-brand-board.png    <- Planche récapitulative officielle             |
|  ├── logo/                                                                                        |
|  │   ├── pyingestkit-logo-horizontal.png (.webp) <- Logo complet horizontal standard              |
|  │   ├── pyingestkit-logo-horizontal@2x.png      <- Version Retina / High-DPI                     |
|  │   ├── pyingestkit-primary-lockup-dark.png     <- Lockup contrasté pour fond sombre/navy        |
|  │   ├── pyingestkit-primary-lockup-light.png    <- Lockup contrasté pour fond clair/blanc        |
|  │   ├── pyingestkit-logo-vertical.png           <- Version verticale / format carré              |
|  │   └── pyingestkit-logo-horizontal-*.svg       <- Conteneur SVG raster-preserving               |
|  ├── mark/                                                                                        |
|  │   ├── pyingestkit-pik-mark-color.png (.webp)  <- Pictogramme PIK isolé couleur                 |
|  │   ├── pyingestkit-pik-mark-color@2x.png       <- Pictogramme Retina                            |
|  │   ├── pyingestkit-pik-mark-monochrome.png     <- Pictogramme monochrome pour impression / CLI  |
|  │   ├── pyingestkit-pik-icon-dark.png           <- Icône d'application fond sombre               |
|  │   └── pyingestkit-pik-mark-*.svg              <- Conteneur SVG mark                            |
|  ├── favicon/                                                                                     |
|  │   ├── favicon.ico                             <- Multi-résolution pour navigateurs desktop     |
|  │   ├── favicon-16x16.png, favicon-32x32.png    <- Tailles standards onglets                     |
|  │   ├── apple-touch-icon.png                    <- Format 180x180 pour iOS                       |
|  │   ├── android-chrome-192x192 / 512x512.png    <- Formats PWA / Android                         |
|  │   └── pyingestkit-icon-*.png (16 à 512)       <- Déclinaisons matricielles d'icônes            |
|  ├── social/                                                                                      |
|  │   ├── pyingestkit-og-light-1200x630.jpg       <- Carte OpenGraph 1200x630 fond clair           |
|  │   └── pyingestkit-og-dark-1200x630.jpg        <- Carte OpenGraph 1200x630 fond sombre          |
|  └── web/                                                                                         |
|      ├── pyingestkit-brand-tokens.css            <- Variables CSS :root des couleurs              |
|      └── site.webmanifest                        <- Manifest web app standardisé                  |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Cartographie d'Intégration Globale dans le Package

L'intégration doit diffuser la marque de manière fluide et automatique sur l'ensemble des points de contact du framework :

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| FLUX DE PROPAGATION DES ASSETS DE MARQUE DANS LE PACKAGE                                         |
|                                                                                                   |
|  [ Resources : pyingestkit-brand-assets-v1 ]                                                      |
|         │                                                                                         |
|         ├───────────────────> docs/assets/brand/                                                  |
|         │                     ├── logos/ (horizontal, dark/light lockups)                         |
|         │                     ├── marks/ (pik-mark color, dark)                                   |
|         │                     └── social/ (og-light, og-dark)                                     |
|         │                                                                                         |
|         ├───────────────────> docs/assets/favicons/                                               |
|         │                     ├── favicon.ico, favicon-32x32.png, apple-touch-icon.png            |
|         │                     └── site.webmanifest                                                |
|         │                                                                                         |
|         ├───────────────────> docs/stylesheets/extra.css                                          |
|         │                     └── Injection des tokens CSS :root (--pyingestkit-*)                |
|         │                                                                                         |
|         ├───────────────────> README.md                                                           |
|         │                     ├── Hero Lockup centré (support Dark/Light GitHub)                  |
|         │                     └── Tagline officielle : "From any source to reliable datasets"     |
|         │                                                                                         |
|         ├───────────────────> docs/index.md                                                       |
|         │                     └── En-tête documentation officielle avec logo et signature         |
|         │                                                                                         |
|         └───────────────────> mkdocs.yml                                                          |
|                               ├── theme.logo & theme.favicon                                      |
|                               ├── Palette de couleurs Material (primary navy / accent blue)       |
|                               └── OpenGraph metadata (social card 1200x630)                       |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 4. Spécifications Techniques d'Intégration Étape par Étape

### Étape 1 : Création de l'arborescence cible dans `docs/assets/`
Il convient d'importer les fichiers nécessaires dans la documentation pour qu'ils soient servis à la fois par GitHub et par le moteur MkDocs :

```text
pyingestkit/docs/
├── assets/
│   ├── brand/
│   │   ├── pyingestkit-logo-horizontal.png
│   │   ├── pyingestkit-primary-lockup-dark.png
│   │   ├── pyingestkit-primary-lockup-light.png
│   │   ├── pyingestkit-pik-mark-color.png
│   │   ├── pyingestkit-og-dark-1200x630.jpg
│   │   └── pyingestkit-og-light-1200x630.jpg
│   ├── favicons/
│   │   ├── favicon.ico
│   │   ├── favicon-16x16.png
│   │   ├── favicon-32x32.png
│   │   ├── apple-touch-icon.png
│   │   └── site.webmanifest
│   └── brand-tokens.css
└── stylesheets/
    └── brand.css
```

---

### Étape 2 : Configuration MkDocs Material (`mkdocs.yml`)
Mettre à niveau [`mkdocs.yml`](../../mkdocs.yml) pour exploiter les assets officiels, la double palette jour/nuit et les variables de couleur :

```yaml
site_name: PyIngestKit
site_description: From any source to reliable datasets. Composable batch ingestion and governance for Python.
site_url: https://tawounfouet.github.io/pyingestkit/

theme:
  name: material
  logo: assets/brand/pyingestkit-pik-mark-color.png
  favicon: assets/favicons/favicon.ico
  palette:
    # Mode Clair
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: custom
      accent: blue
      toggle:
        icon: material/brightness-7
        name: Passer au mode sombre
    # Mode Sombre
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: custom
      accent: cyan
      toggle:
        icon: material/brightness-4
        name: Passer au mode clair

extra_css:
  - assets/brand-tokens.css
  - stylesheets/brand.css

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/tawounfouet/pyingestkit
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/pyingestkit/
```

Fichier `docs/stylesheets/brand.css` associé pour lier les tokens :
```css
/* Intégration des couleurs PyIngestKit dans Material for MkDocs */
[data-md-color-primary="custom"] {
  --md-primary-fg-color: #0B2447;
  --md-primary-fg-color--light: #2563EB;
  --md-primary-fg-color--dark: #07172E;
}
```

---

### Étape 3 : Intégration dans le README GitHub (`README.md`)
Pour que le logo s'affiche parfaitement sur GitHub aussi bien en mode sombre qu'en mode clair, on utilise la balise native GitHub `<picture>` :

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/pyingestkit-primary-lockup-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/pyingestkit-primary-lockup-light.png">
    <img src="docs/assets/brand/pyingestkit-logo-horizontal.png" alt="PyIngestKit — From any source to reliable datasets" width="460">
  </picture>
</p>

<p align="center">
  <strong>From any source to reliable datasets.</strong><br>
  <em>Acquire → Process → Validate → Publish</em>
</p>
```

---

### Étape 4 : Métadonnées OpenGraph & Social Cards
Ajouter dans le bloc `<head>` des templates HTML de MkDocs (via `overrides/main.html` si souhaité) ou dans `mkdocs.yml` :
```yaml
extra:
  generator: false
  social_card:
    image: assets/brand/pyingestkit-og-dark-1200x630.jpg
```
Sur GitHub : définir l'image de prévisualisation du repository dans les **Settings > General > Social preview** en sélectionnant `social/pyingestkit-og-dark-1200x630.jpg`.

---

## 5. Règles d'Utilisation & Brand Governance

1. **Intégrité du Mark PIK** :
   - Ne jamais déformer, étirer ou modifier les proportions du pictogramme.
   - Ne pas changer les teintes internes du cube/symbole hors de la palette approuvée (`#0B2447`, `#2563EB`, `#06B6D4`, `#10B981`).
2. **Gestion des Arrière-plans** :
   - Sur fond clair : privilégier [`pyingestkit-primary-lockup-light.png`](../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-primary-lockup-light.png) ou [`pyingestkit-logo-horizontal.png`](../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-logo-horizontal.png).
   - Sur fond sombre ou navy : utiliser impérativement [`pyingestkit-primary-lockup-dark.png`](../../../resources/pyingestkit-brand-assets-v1/logo/pyingestkit-primary-lockup-dark.png) (qui intègre le lettrage blanc et les contrastes ajustés) plutôt qu'un filtre négatif artificiel.
3. **Usage Minimaliste & CLI** :
   - Pour les environnements terminaux ou l'impression sans couleur, employer exclusivement [`pyingestkit-pik-mark-monochrome.png`](../../../resources/pyingestkit-brand-assets-v1/mark/pyingestkit-pik-mark-monochrome.png).
4. **Icons et Favicons** :
   - Le mark seul (sans lettrage) doit être utilisé pour les favicons de navigateurs, l'icône de package PyPI, et les avatars d'organisation.

---

## 6. Plan d'Action pour le Déploiement

| Priorité | Action | Fichiers touchés |
| :--- | :--- | :--- |
| **P1** | Copier les assets essentiels du brand kit dans `docs/assets/` | `docs/assets/brand/`, `docs/assets/favicons/` |
| **P2** | Injecter le lockup adaptatif Dark/Light et les signatures dans `README.md` | `README.md` |
| **P3** | Configurer MkDocs (`theme.logo`, `theme.favicon`, `extra_css`) | `mkdocs.yml`, `docs/stylesheets/brand.css` |
| **P4** | Mettre à jour l'en-tête de la page d'accueil de la doc | `docs/index.md` |
| **P5** | Uploader la Social Preview 1200x630 sur le repository GitHub | GitHub Repository Settings |
