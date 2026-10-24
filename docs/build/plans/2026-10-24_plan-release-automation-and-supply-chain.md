# Plan d'Implémentation : Automatisation Release, PyPI Trusted Publishing, Supply Chain & Gouvernance CI/CD

- **Projet** : PyIngestKit
- **Statut** : Prêt pour implémentation
- **Date** : 24 Octobre 2026
- **Auteur** : Antigravity / Pair Programming
- **Document source** : [`../../analyses/2026-10-24_ci-cd-and-release-engineering-comparison.md`](../../analyses/2026-10-24_ci-cd-and-release-engineering-comparison.md)
- **Branche cible** : `feat/ci-release-automation-and-governance`

---

## 1. Objectifs & Périmètre

Ce plan d'implémentation met en œuvre les améliorations extraites des packages frères `pyworkflowkit` et `pytransformkit` pour porter l'ingénierie de release et la chaîne d'approvisionnement (*Software Supply Chain*) de **PyIngestKit** au meilleur standard de sécurité et d'automatisation :

1. **Suppression des secrets statiques** : Remplacement du jeton d'API PyPI local ([`.env`](../../../.env)) par l'authentification **PyPI Trusted Publishing (OIDC)** native entre GitHub Actions et PyPI.
2. **Attestations Cryptographiques Sigstore (SLSA)** : Signature et publication automatique de la provenance des builds (`actions/attest-build-provenance`).
3. **Software Bill of Materials (SBOM)** : Génération d'un inventaire de dépendances standardisé **CycloneDX** attaché à chaque release.
4. **Automatisation de bout en bout** : Publication déclenchée sur publication d'une GitHub Release (`release: types: [published]`) ou par `workflow_dispatch` d'un tag qualifié.
5. **Gouvernance Git & RFC-001** : Mise en place d'un [`.github/pull_request_template.md`](../../../.github/pull_request_template.md) pour verrouiller les invariants d'architecture (CAS, Ledgers, GC, Wire contracts).
6. **Optimisation des performances CI** : Filtrage des branches dans [`ci.yml`](../../../.github/workflows/ci.yml) et activation du cache Pip.
7. **Visibilité & Ergonomie Publique** : Intégration des badges officiels PyPI et Documentation sur le [`README.md`](../../../README.md).

---

## 2. Diagramme d'Architecture du Pipeline de Release

```text
                  +───────────────────────────────+
                  |  Nouvelle Release / Tag Git   |
                  +───────────────────────────────+
                                  │
                                  ▼
                     [ Gate 1: Format & Identité ]
                     - Tag == 'vX.Y.Z' ?
                     - Tag == package version ?
                                  │  OUI
                                  ▼
                     [ Gate 2: CI Status Check ]
                     - SHA qualifié sur Python 3.11-3.14 ?
                     - Tests d'architecture verts ?
                     - Sécurité & Conformance validés ?
                                  │  OUI
                                  ▼
                     [ Gate 3: Build & Provenance ]
                     - `python -m build` & `twine check`
                     - CycloneDX SBOM generated
                     - Sigstore Provenance Attestation
                                  │  OUI
                                  ▼
            +─────────────────────┴─────────────────────+
            │                                           │
            ▼                                           ▼
+────────────────────────+                 +────────────────────────+
| PyPI Trusted Publish   |                 | GitHub Release Assets  |
| (Échange de jeton OIDC)|                 | (Attachement complet)  |
+────────────────────────+                 +────────────────────────+
            │
            ▼
+────────────────────────+
| Public Consumer Smoke  |
| (pip install clean)    |
+────────────────────────+
```

---

## 3. Cartographie des Fichiers

```text
.github/
├── pull_request_template.md            # [CRÉATION] Template PR formalisant l'architecture & les invariants
└── workflows/
    ├── ci.yml                          # [MODIFICATION] Filtrage branches main, activation cache pip
    └── publish-pypi.yml                # [CRÉATION] Workflow OIDC + SBOM + Sigstore + Attach Release

scripts/
└── public_consumer_smoke.py           # [CRÉATION] Script de vérification consommateur public post-PyPI

pyproject.toml                          # [MODIFICATION] Enrichissement des URLs de projet PEP 621
README.md                               # [MODIFICATION] Ajout des badges officiels PyPI et Docs
.env                                    # [NETTOYAGE] Retrait du token statique PyPI après bascule OIDC
```

---

## 4. Spécifications Détaillées par Phase

### Phase 1 — Template de Pull Request & Gouvernance d'Architecture
**Fichier à créer :** [`.github/pull_request_template.md`](../../../.github/pull_request_template.md)

Le template guide les contributeurs et agents pour prévenir toute régression sur les contrats gelés de la ligne 2.x :

```markdown
## Summary
Description concise du changement et du comportement introduit ou modifié.

## Architecture Impact (RFC-001 & Invariants V2)
- Quelle responsabilité PyIngestKit ce changement concerne-t-il ?
- Affecte-t-il un invariant de gouvernance (Compare-and-Swap, Ledgers durables, Holds, GC sécurisé, Governed Rollback) ?
- Traverse-t-il une frontière Domain / Port / Adapter ?

## Compatibility & Contract Checklist
- [ ] Root public API (`from pyingestkit import ...`) : aucune rupture
- [ ] Qualified governance namespaces (`pyingestkit.governance.*`) : conforme
- [ ] Schéma de persistance PostgreSQL (`schema_version = 1`) : inchangé ou migration fournie
- [ ] Boundary wire contracts / sérialisation (`tests/contract/fixtures/`) : conforme
- [ ] Compatibilité 1.x / V1 migration : préservée
- [ ] Aucun changement de contrat non documenté

## Verification Checklist
- [ ] Tests unitaires V2 (`tests/unit/v2`)
- [ ] Tests d'architecture (`tests/architecture`)
- [ ] Tests de conformité des connecteurs (`tests/conformance/v2`)
- [ ] Tests d'intégration multi-providers (`tests/integration/v2`)
- [ ] Qualité & Typage (`make quality`)
- [ ] Sécurité (`make security`)
- [ ] Build & Smoke Wheel (`make verify`)

## Notes
Considérations de migration, limitations connues ou travaux reportés.
```

---

### Phase 2 — Optimisation & Hygiène de la CI
**Fichier à modifier :** [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml)

#### Modifications requises :
1. **Restreindre les déclencheurs de push** :
   Remplacer :
   ```yaml
   on:
     push:
     pull_request:
   ```
   Par :
   ```yaml
   on:
     push:
       branches: [main]
     pull_request:
   ```
2. **Activer le cache Pip** sur chaque étape `actions/setup-python` :
   ```yaml
         - uses: actions/setup-python@v5
           with:
             python-version: ${{ matrix.python-version }}
             cache: pip
   ```

---

### Phase 3 — Workflow de Publication PyPI Automatisée & Supply Chain
**Fichier à créer :** [`.github/workflows/publish-pypi.yml`](../../../.github/workflows/publish-pypi.yml)

```text
+------------------------------------------------------------------------------------------------+
| FLUX DU WORKFLOW PUBLISH-PYPI.YML                                                              |
|                                                                                                |
|  [ release: published ] ──> [ Resolve Tag vX.Y.Z ] ──> [ Verify version in code ]               |
|                                                               │                                |
|                                                               ▼                                |
|  [ Sigstore Provenance ] <── [ Generate SBOM & SHA256 ] <── [ Verify CI on exact SHA ]         |
|             │                                                                                  |
|             ▼                                                                                  |
|  +─────────────────────────────────────────+─────────────────────────────────────────+        |
|  │                                         │                                         │        |
|  ▼                                         ▼                                         ▼        |
|  [ OIDC PyPI Publish ]            [ Attach Assets to Release ]            [ Consumer Smoke ]   |
+------------------------------------------------------------------------------------------------+
```

#### Code du workflow :
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      release_tag:
        description: "Tag immuable existant à publier (ex: v2.1.0)"
        required: true
        type: string

permissions:
  contents: read

jobs:
  build-and-publish:
    name: Build distributions and publish to PyPI
    runs-on: ubuntu-latest
    permissions:
      id-token: write     # OIDC requis pour PyPI Trusted Publishing
      contents: write     # Requis pour attacher le SBOM et les hashs à la Release GitHub
      actions: read       # Requis pour vérifier la qualification du commit
      attestations: write # Requis pour Sigstore build provenance

    environment:
      name: pypi
      url: https://pypi.org/p/pyingestkit

    steps:
      - name: Resolve immutable release tag
        id: release
        shell: bash
        env:
          EVENT_NAME: ${{ github.event_name }}
          RELEASE_EVENT_TAG: ${{ github.event.release.tag_name }}
          DISPATCH_TAG: ${{ inputs.release_tag }}
        run: |
          set -euo pipefail
          if [ "$EVENT_NAME" = "release" ]; then
            RELEASE_TAG="$RELEASE_EVENT_TAG"
          else
            RELEASE_TAG="$DISPATCH_TAG"
          fi

          case "$RELEASE_TAG" in
            v[0-9]*.[0-9]*.[0-9]*) ;;
            *)
              echo "Publishing requires an immutable vX.Y.Z tag; got: $RELEASE_TAG" >&2
              exit 1
              ;;
          esac
          echo "tag=$RELEASE_TAG" >> "$GITHUB_OUTPUT"

      - name: Checkout release tag
        uses: actions/checkout@v4
        with:
          ref: ${{ steps.release.outputs.tag }}
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Validate release tag against package version
        id: identity
        shell: bash
        env:
          RELEASE_TAG: ${{ steps.release.outputs.tag }}
        run: |
          set -euo pipefail
          TAG_VERSION="${RELEASE_TAG#v}"
          PACKAGE_VERSION="$(python - <<'PY'
          import tomllib
          from pathlib import Path
          pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
          from pyingestkit._version import __version__
          print(__version__)
          PY
          )"
          RELEASE_SHA="$(git rev-parse HEAD)"

          if [ "$TAG_VERSION" != "$PACKAGE_VERSION" ]; then
            echo "Tag/package version mismatch: tag=$TAG_VERSION package=$PACKAGE_VERSION" >&2
            exit 1
          fi

          echo "sha=$RELEASE_SHA" >> "$GITHUB_OUTPUT"
          echo "version=$PACKAGE_VERSION" >> "$GITHUB_OUTPUT"

      - name: Require successful CI for exact release SHA
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          RELEASE_SHA: ${{ steps.identity.outputs.sha }}
        run: |
          set -euo pipefail
          SUCCESSFUL_RUNS="$(gh api -X GET \
            "repos/$GITHUB_REPOSITORY/actions/workflows/ci.yml/runs" \
            -f head_sha="$RELEASE_SHA" \
            -f status="success" \
            -f per_page=100 \
            --jq '.workflow_runs | length')"

          if [ "$SUCCESSFUL_RUNS" -lt 1 ]; then
            echo "No successful CI workflow run found for SHA $RELEASE_SHA" >&2
            exit 1
          fi

      - name: Build sdist and wheel
        run: |
          set -euo pipefail
          python -m pip install --upgrade pip build twine cyclonedx-bom
          python -m build
          python -m twine check dist/*
          mkdir -p pypi-dist release-assets
          cp dist/*.whl dist/*.tar.gz pypi-dist/
          cp pypi-dist/*.whl pypi-dist/*.tar.gz release-assets/

      - name: Generate CycloneDX SBOM
        run: |
          cyclonedx-py environment -o release-assets/pyingestkit-cyclonedx.json

      - name: Generate and verify SHA256 checksums
        shell: bash
        run: |
          set -euo pipefail
          cd release-assets
          sha256sum *.whl *.tar.gz pyingestkit-cyclonedx.json > SHA256SUMS
          sha256sum -c SHA256SUMS

      - name: Generate Artifact Attestations (Sigstore)
        uses: actions/attest-build-provenance@v2
        with:
          subject-path: "release-assets/*"

      - name: Attach artifacts to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ steps.release.outputs.tag }}
          files: |
            release-assets/*
          fail_on_unmatched_files: true

      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@v1
        with:
          packages-dir: pypi-dist/

  public-consumer-smoke:
    name: Verify public PyPI consumer
    needs: [build-and-publish]
    runs-on: ubuntu-latest
    steps:
      - name: Checkout release tag
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.release.tag_name || inputs.release_tag }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Wait for PyPI propagation and verify consumer
        run: |
          python scripts/public_consumer_smoke.py --package pyingestkit
```

---

### Phase 4 — Script de Smoke Test Consommateur Public
**Fichier à créer :** [`scripts/public_consumer_smoke.py`](../../../scripts/public_consumer_smoke.py)

Ce script autonome :
1. Lit la version cible dans [`pyproject.toml`](../../../pyproject.toml) ou accepte un argument `--expected-version`.
2. Interroge `https://pypi.org/pypi/pyingestkit/<version>/json` pendant un maximum de 10 minutes (polling toutes les 15s).
3. Crée un virtualenv temporaire vierge.
4. Installe `pyingestkit[postgres,s3]==<version>` sans cache.
5. Exécute un smoke test vérifiant les imports racines 2.x, les namespaces de gouvernance, et l'instanciation de l'IngestionRuntime.

---

### Phase 5 — Enrichissement des Métadonnées & Badges README

#### 1. Métadonnées PEP 621 dans [`pyproject.toml`](../../../pyproject.toml) :
Ajout de la section standardisée `[project.urls]` :
```toml
[project.urls]
Homepage = "https://github.com/tawounfouet/pyingestkit"
Documentation = "https://tawounfouet.github.io/pyingestkit/"
Repository = "https://github.com/tawounfouet/pyingestkit.git"
Changelog = "https://github.com/tawounfouet/pyingestkit/blob/main/CHANGELOG.md"
Issues = "https://github.com/tawounfouet/pyingestkit/issues"
```

#### 2. Nouveaux Badges dans [`README.md`](../../../README.md) :
Remplacement de l'en-tête par :
```markdown
# PyIngestKit

[![CI](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/ci.yml)
[![Security](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml/badge.svg)](https://github.com/tawounfouet/pyingestkit/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/pyingestkit.svg)](https://pypi.org/project/pyingestkit/)
[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stable: 2.1.0](https://img.shields.io/badge/stable-2.1.0-brightgreen.svg)](docs/releases/v2.1.0.md)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://tawounfouet.github.io/pyingestkit/)
```

---

### Phase 6 — Activation PyPI Trusted Publishing & Nettoyage

1. **Configuration côté PyPI (One-off UI)** :
   - Se rendre sur [https://pypi.org/manage/project/pyingestkit/settings/publishing/](https://pypi.org/manage/project/pyingestkit/settings/publishing/).
   - Ajouter un Trusted Publisher GitHub Actions :
     - **Owner** : `tawounfouet`
     - **Repository name** : `pyingestkit`
     - **Workflow name** : `publish-pypi.yml`
     - **Environment name** : `pypi`
2. **Nettoyage local** :
   - Supprimer le jeton `API_TOKEN` de [`.env`](../../../.env) une fois la première release OIDC validée.

---

## 5. Matrice de Risques & Stratégie de Déploiement

| Risque identifié | Probabilité | Impact | Mesure de mitigation |
| :--- | :--- | :--- | :--- |
| Conflit de version Tag vs Package | Faible | Élevé | Étape bloquante `Validate release tag against package version` |
| Publication d'un commit non qualifié | Très faible | Critique | Étape `Require successful CI for exact release SHA` via GitHub API |
| Délai de propagation PyPI entraînant un échec du Smoke Test | Moyen | Faible | Polling exponentiel avec timeout de 10 min dans `public_consumer_smoke.py` |
| Attestation Sigstore rejetée | Très faible | Faible | Permission explicite `attestations: write` déclarée sur le job |

---

## 6. Critères d'Acceptation & Validation

- [ ] [`.github/pull_request_template.md`](../../../.github/pull_request_template.md) est présent et pré-rempli sur toute nouvelle PR.
- [ ] [`ci.yml`](../../../.github/workflows/ci.yml) ne se déclenche plus sur les branches de travail secondaires (hors PRs).
- [ ] Le build `make verify` et la suite de tests passent intégralement en local.
- [ ] [`README.md`](../../../README.md) affiche les badges PyPI et Docs fonctionnels avec redirection correcte.
- [ ] Un test `workflow_dispatch` (ou une future release `2.1.1`) exécute avec succès `publish-pypi.yml` sans intervention manuelle.
- [ ] Les artefacts (wheel, tar.gz, SBOM, SHA256SUMS) sont automatiquement présents sur la Release GitHub.
