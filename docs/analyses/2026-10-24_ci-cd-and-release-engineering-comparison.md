# Analyse Comparative CI/CD & Release Engineering : PyIngestKit vs PyTransformKit & PyWorkflowKit

**Date :** 24 Octobre 2026  
**Auteur :** Antigravity / Pair Programming  
**Contexte :** Clôture du LOT-30 (PyIngestKit 2.1.0 stable), publication PyPI et identification des écarts d'automatisation avec les packages frères ([PyTransformKit](../../../pytransformkit), [PyWorkflowKit](../../../pyworkflowkit)).

---

## 1. Contexte & Problématique

Lors de la clôture de la ligne **PyIngestKit 2.1.0 (LOT-30)**, le repository et la qualification post-merge (`main` à `625d733d01cd9eb23272e2ad16af27628e648529`) étaient entièrement verts. Toutefois, l'index public **PyPI affichait toujours la version historique 1.0.1** (datant de septembre 2026).

L'analyse de l'infrastructure CI/CD a mis en évidence trois causes directes :
1. **Absence de workflow de release/publication PyPI :** Le dossier [`.github/workflows/`](../../.github/workflows) ne comportait aucun job dédié à l'empaquetage et au déploiement sur PyPI lors de la création d'un tag ou d'une release GitHub.
2. **Processus de publication historique manuel :** La publication dépendait d'un jeton statique stocké dans un fichier local [`.env`](../../.env) (`API_TOKEN="pypi-..."`) exploité manuellement avec Twine.
3. **Désynchronisation entre Git et PyPI :** Même la version `2.0.0` n'avait jamais été publiée sur PyPI, bien que tagguée dans Git.

```text
+---------------------------------------------------------------------------------------------------+
| DIAGNOSTIC DE L'ÉCART HISTORIQUE DANS PYINGESTKIT                                                |
|                                                                                                   |
|  [Dev Machine] ────────> build local ──> .env (API_TOKEN) ──> twine upload ──> [ PyPI ]         |
|         │                                                          ▲                              |
|         │                                            MANUEL        │ (Version 2.0.0 oubliée,      |
|         └──────────────> git tag / push ───────────────────────────┘  restée en 1.0.1 sur PyPI)   |
+---------------------------------------------------------------------------------------------------+
```

À titre de comparaison, les deux autres packages frères du monorepo ([`pytransformkit`](../../../pytransformkit) et [`pyworkflowkit`](../../../pyworkflowkit)) disposent de chaînes de publication automatisées, sécurisées et d'outils de gouvernance CI/CD plus avancés. Ce document synthétise les meilleures pratiques à extraire de ces projets pour moderniser PyIngestKit.

---

## 2. Matrice Comparative Globale

| Fonctionnalité / Outil | PyIngestKit (Actuel) | PyTransformKit | PyWorkflowKit |
| :--- | :--- | :--- | :--- |
| **Publication PyPI** | Manuelle via `twine` et [`.env`](../../.env) local | Automatisée via [`publish-pypi.yml`](../../../pytransformkit/.github/workflows/publish-pypi.yml) | Automatisée via [`publish-pypi.yml`](../../../pyworkflowkit/.github/workflows/publish-pypi.yml) |
| **Authentification PyPI** | Jeton API statique à long terme | Trusted Publishing (OIDC) | Trusted Publishing (OIDC) |
| **Déclencheurs de Release** | Manuel en local | `release: [published]` + push sentinelle | `release: [published]` + `workflow_dispatch` |
| **Vérification Tag / Version** | Aucune (manuel) | Oui (contrôle Python `tomllib`) | Oui (contrôle bash + `tomllib`) |
| **Garde-fou CI Release SHA** | Manuel | Vérification freeze contractuel | API GitHub vérifiant la qualification exacte du SHA |
| **Génération SBOM** | Aucune | Aucune | CycloneDX (`cyclonedx-py`) |
| **Attestation Provenance** | Aucune | Aucune | Sigstore (`actions/attest-build-provenance`) |
| **Release GitHub automatisée** | Manuelle (`gh release create`) | Automatique via `gh release` CLI | Automatique via `softprops/action-gh-release` |
| **Smoke Test PyPI Public** | Aucun | Oui (`public-consumer-smoke`) | Prévu / qualification locale |
| **Template de Pull Request** | ❌ Aucun | ❌ Aucun | ✅ [`.github/pull_request_template.md`](../../../pyworkflowkit/.github/pull_request_template.md) |
| **Filtres de branches CI ([`ci.yml`](../../.github/workflows/ci.yml))** | ❌ `on: push` (toutes branches) | ✅ `push: branches: [main]` | ✅ `push: branches: [main]` |
| **Cache Pip en CI** | ❌ Non configuré | ✅ `cache: pip` | ✅ `cache: pip` |
| **Badges [README.md](../../README.md)** | CI, Security, Python, MIT, Stable | CI, Overview Image, Status | CI, Architecture, Status |

---

## 3. Architecture Cible : Supply Chain Sécurisée & Automatisée

Le diagramme ASCII ci-dessous illustre l'architecture cible standardisée à mettre en œuvre dans PyIngestKit en combinant les atouts de PyWorkflowKit et PyTransformKit :

```text
+---------------------------------------------------------------------------------------------------+
| ARCHITECTURE CIBLE : SECURE SUPPLY CHAIN & TRUSTED PUBLISHING                                    |
|                                                                                                   |
|  [ GitHub Release vX.Y.Z ]  OU  [ workflow_dispatch (Tag) ]                                       |
|             │                                                                                     |
|             ▼                                                                                     |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|  | GitHub Actions : .github/workflows/publish-pypi.yml                                         |  |
|  |                                                                                             |  |
|  |  Étape 1 : Gate Identité ────> Tag == 'vX.Y.Z' == version dans pyproject.toml                 |  |
|  |  Étape 2 : Gate CI Status ───> Commit exact qualifié et vert sur ci.yml (API GitHub)       |  |
|  |  Étape 3 : Build Isolé ──────> python -m build (wheel & sdist)                              |  |
|  |  Étape 4 : Supply Chain ─────> CycloneDX SBOM JSON + SHA256SUMS                             |  |
|  |  Étape 5 : Cryptographie ────> Attestations Sigstore (actions/attest-build-provenance)       |  |
|  +─────────────────────────────────────────────────────────────────────────────────────────────+  |
|             │                                                  │                                  |
|     (OIDC Exchange)                                     (Upload Assets)                           |
|             ▼                                                  ▼                                  |
|   +──────────────────+                              +──────────────────────────+                  |
|   |   PyPI Registry  |                              |  GitHub Release vX.Y.Z   |                  |
|   | (Zero Secret ID) |                              | (.whl, .tar.gz, SBOM,    |                  |
|   +──────────────────+                              |  SHA256SUMS, Provenance) |                  |
|             │                                       +──────────────────────────+                  |
|      (CDN Broadcast)                                                                              |
|             ▼                                                                                     |
|   +──────────────────────────────────+                                                            |
|   | Job : public-consumer-smoke      |                                                            |
|   | 1. Polling propagation PyPI      |                                                            |
|   | 2. venv vierge                   |                                                            |
|   | 3. pip install pyingestkit==X.Y.Z|                                                            |
|   | 4. Validation runtime des extras |                                                            |
|   +──────────────────────────────────+                                                            |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Détail des Bonnes Pratiques à Extraire

### A. Publication PyPI Automatisée & Trusted Publishing (OIDC)
*Inspiré de : [`pyworkflowkit/.../publish-pypi.yml`](../../../pyworkflowkit/.github/workflows/publish-pypi.yml) et [`pytransformkit/.../publish-pypi.yml`](../../../pytransformkit/.github/workflows/publish-pypi.yml)*

#### Les limites actuelles de PyIngestKit
- L'utilisation d'un token statique dans un fichier local [`.env`](../../.env) expose à des risques de fuite de credentials, d'oubli lors d'une release, ou de rupture si le développeur change de machine ou d'environnement.
- Aucune exécution reproductible dans un runner éphémère.

#### La solution éprouvée
1. **Trusted Publishing (OIDC)** : Élimine les tokens permanents au profit d'échanges de tokens JWT cryptographiques de courte durée entre GitHub Actions et PyPI :
   ```yaml
   permissions:
     id-token: write
     contents: read
   steps:
     - name: Publish to PyPI
       uses: pypa/gh-action-pypi-publish@v1
   ```
2. **Garde-fous d'identité de release** :
   Le workflow vérifie que :
   - Le tag respecte la convention immuable `vX.Y.Z`.
   - La version déclarée dans [`src/pyingestkit/_version.py`](../../src/pyingestkit/_version.py) et [`pyproject.toml`](../../pyproject.toml) correspond rigoureusement au tag git.
   - Le commit exact du tag a validé la totalité de la matrice de test et des gates de sécurité avant que la distribution ne soit poussée.

---

### B. Supply Chain Security : Attestations Sigstore & SBOM CycloneDX
*Inspiré de : [`pyworkflowkit/.../publish-pypi.yml`](../../../pyworkflowkit/.github/workflows/publish-pypi.yml)*

#### Les limites actuelles de PyIngestKit
- Les sommes de contrôle SHA256 sont calculées à la main lors du tagging.
- Aucun inventaire de dépendances (SBOM) n'est produit pour les auditeurs de sécurité ou les consommateurs d'entreprise.

#### La solution éprouvée
1. **Génération d'un SBOM CycloneDX standardisé** :
   ```bash
   cyclonedx-py environment -o release-assets/pyingestkit-cyclonedx.json
   ```
2. **Signature et Attestation de Build Sigstore (SLSA Level 2+)** :
   ```yaml
   - name: Generate Artifact Attestations (Sigstore)
     uses: actions/attest-build-provenance@v2
     with:
       subject-path: "release-assets/*"
   ```
3. **Publication automatique des assets** :
   Attacher directement les distributions (`.whl`, `.tar.gz`), le fichier `SHA256SUMS` et le `pyingestkit-cyclonedx.json` sur la GitHub Release officielle.

---

### C. Validation Post-Déploiement : Public Consumer Smoke Test
*Inspiré de : [`pytransformkit/.../publish-pypi.yml`](../../../pytransformkit/.github/workflows/publish-pypi.yml)*

#### Les limites actuelles de PyIngestKit
- Une fois le paquet téléversé, rien ne garantit que le paquet est immédiatement installable sans conflit d'extras ou d'incompatibilité de métadonnées depuis l'index mondial PyPI.

#### La solution éprouvée
Un job CI exécuté après la publication qui :
1. Interroge en boucle l'API HTTP PyPI (`https://pypi.org/pypi/pyingestkit/<version>/json`) pour attendre la propagation du CDN.
2. Crée un environnement virtuel temporaire propre.
3. Exécute :
   ```bash
   pip install --no-cache-dir "pyingestkit[postgres,s3]==<version>"
   python -c "import pyingestkit; print(pyingestkit.__version__)"
   ```
4. Exécute le smoke test consommateur ([`scripts/wheel_smoke_test.py`](../../scripts/wheel_smoke_test.py)).

---

### D. Formalisation de la Gouvernance Git : Pull Request Template
*Inspiré de : [`pyworkflowkit/.../pull_request_template.md`](../../../pyworkflowkit/.github/pull_request_template.md)*

#### Les limites actuelles de PyIngestKit
- PyIngestKit est un framework avec des contrats d'architecture stricts (RFC-001, dual-ledger, CAS filesystem/S3, garbage collection sécurisé, wire contracts versionnés).
- Les revues de code reposent uniquement sur la vigilance humaine sans checklist obligatoire dans l'interface de GitHub.

#### La solution éprouvée
Créer [`.github/pull_request_template.md`](../../.github/pull_request_template.md) structuré pour encadrer les PRs de gouvernance et de connecteurs.

---

### E. Optimisations de la CI & Clarté du README

#### 1. Filtrage des déclencheurs et cache dans [`ci.yml`](../../.github/workflows/ci.yml)
- **Problème :** `ci.yml` se déclenche sur n'importe quel push de branche intermédiaire.  
- **Correction :** Restreindre à `push: branches: [main]` et ajouter `cache: pip` sur `actions/setup-python`.

#### 2. Actualisation des Badges sur [`README.md`](../../README.md)
Ajout des badges attestant de la présence officielle sur PyPI et de la disponibilité de la documentation :
```markdown
[![PyPI version](https://img.shields.io/pypi/v/pyingestkit.svg)](https://pypi.org/project/pyingestkit/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/pyingestkit.svg)](https://pypi.org/project/pyingestkit/)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://tawounfouet.github.io/pyingestkit/)
```

---

## 5. Plan d'Action Recommandé

| Étape | Livrable | Complexité | Bénéfice |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Création de [`.github/pull_request_template.md`](../../.github/pull_request_template.md) | Très faible | Standardisation immédiate des revues et respect des invariants V2 |
| **Phase 2** | Ajout des badges PyPI et Docs sur [`README.md`](../../README.md) | Très faible | Clarté et visibilité publique immédiate |
| **Phase 3** | Optimisation de [`ci.yml`](../../.github/workflows/ci.yml) (branches et `cache: pip`) | Faible | Économie de temps et de ressources CI |
| **Phase 4** | Création de [`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml) | Moyenne | Automatisation complète, provenance Sigstore, zéro token permanent |
| **Phase 5** | Suppression du token statique dans [`.env`](../../.env) après bascule OIDC | Très faible | Sécurité et hygiène du repository |
