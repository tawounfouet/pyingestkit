# Rapport de Qualification de Distribution & Supply Chain : <Version>

<!-- 
NOMENCLATURE DU FICHIER :
docs/build/reports/dist/YYYY-MM-DD_<version>_distribution-qualification-report.md
Exemple : docs/build/reports/dist/2026-10-25_v2.2.0_distribution-qualification-report.md
-->

- **Version Déployée :** <!-- ex: v2.2.0 -->
- **Date de Publication :** YYYY-MM-DD
- **Opérateur / Agent :** <!-- Antigravity / AWF / CI Runner -->
- **Commit SHA Scellé :** `abcdef12`
- **Tag Git Associé :** `vX.Y.Z`
- **Workflow de Déploiement :** GitHub Actions `publish-pypi.yml` (Run ID `XXXXXXXXXX`)
- **Résultat Global :** ✅ **DISTRIBUTION QUALIFIÉE & LIVE SUR PYPI** <!-- QUALIFIÉE | ÉCHEC -->

---

## 1. Inventaire des Artefacts Distribués

| Nom de l'Artefact | Type d'Artefact | Taille | Empreinte Cryptographique (SHA-256) |
| :--- | :--- | :---: | :--- |
| `pyingestkit-<version>-py3-none-any.whl` | Wheel Python | `XXX KiB` | `sha256:...` |
| `pyingestkit-<version>.tar.gz` | Source Distribution (sdist) | `XXX KiB` | `sha256:...` |
| `pyingestkit-cyclonedx.json` | SBOM CycloneDX JSON | `XXX KiB` | `sha256:...` |
| `SHA256SUMS` | Manifeste d'intégrité | `XXX B` | `sha256:...` |

---

## 2. Conformité du Packaging (`twine check`)

```text
Checking dist/pyingestkit-<version>-py3-none-any.whl: PASSED
Checking dist/pyingestkit-<version>.tar.gz: PASSED
```

- [x] Description README rendue correctement en Markdown.
- [x] Métadonnées PEP 621 et URLs officielles renseignées.
- [x] Aucune dépendance non déclarée ou résolue hors spec.

---

## 3. Preuves de Supply Chain & Sécurité

- [x] **SBOM CycloneDX :** Généré via `cyclonedx-py environment` et validé.
- [x] **Attestations de provenance (Sigstore / SLSA) :** Générées via `actions/attest-build-provenance@v2` et intégrées aux assets GitHub.
- [x] **Empreintes d'intégrité SHA256SUMS :** Vérifiées cryptographiquement (`sha256sum -c SHA256SUMS`).
- [x] **Release GitHub :** Artefacts rattachés à [`https://github.com/tawounfouet/pyingestkit/releases/tag/v<version>`](https://github.com/tawounfouet/pyingestkit/releases/tag/v<version>).

---

## 4. Statut de Déploiement Public

- **Index Public PyPI :** [`https://pypi.org/project/pyingestkit/<version>/`](https://pypi.org/project/pyingestkit/<version>/)
- **Mode d'Authentification :** <!-- OIDC Trusted Publishing / API Token -->
- **URL Simple Repository :** `https://pypi.org/simple/pyingestkit/`

---

## 5. Procès-Verbal du Consommateur Public Isolé

Exécution de `scripts/public_consumer_smoke.py --package pyingestkit` dans un environnement virtuel propre :

```json
{
  "public_consumer_smoke": "PASS",
  "package": "pyingestkit",
  "version": "<version>",
  "python": "<python-version>",
  "platform": "<os-platform>"
}
```

### Invariants Vérifiés en Conditions Réelles
- [x] Installation propre depuis l'index PyPI avec extras `[cli,postgres,s3]`.
- [x] Importation de l'API racine `pyingestkit` (exactement 11 symboles publics).
- [x] Présence et intégrité des sous-modules de gouvernance (`governance.rollback`, `PublicationLedger`).
- [x] Binaire CLI `pik --version` et commande d'autodiagnostic `pik doctor --json` (`status: healthy`).

---

## 6. Décision Finale de Certification

Le présent procès-verbal certifie que les artefacts de distribution de la version **`<version>`** sont conformes aux exigences de sécurité, d'intégrité et de traçabilité de `PyIngestKit`.  
La release est officiellement **qualifiée et disponible au public**.
