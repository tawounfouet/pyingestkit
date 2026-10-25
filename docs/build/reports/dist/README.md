# Procès-Verbaux & Rapports de Qualification de Distribution : `docs/build/reports/dist/`

Ce répertoire héberge les **preuves d'intégrité, de packaging et de déploiement** des distributions de [`PyIngestKit`](../../../README.md) (Wheels `.whl`, archives source `.tar.gz`, SBOM CycloneDX, attestations Sigstore / SLSA, et vérifications consommateurs PyPI).

---

## 1. Rôle dans la Supply Chain & Sécurité

Tandis que [`docs/build/reports/tests/`](../tests/) certifie la conformité logique du code source (tests unitaires, d'intégration et d'architecture), ce dossier certifie la **sécurité de la supply chain logicielle et la viabilité des artefacts publiés** :
- **Intégrité des artefacts de build :** Tailles, métadonnées PEP 621 et empreintes SHA-256 (`SHA256SUMS`).
- **Conformité des métadonnées de packaging :** Résultat du contrôle `twine check`.
- **Gouvernance Supply Chain (SBOM) :** Génération et archivage de la nomenclature logicielle CycloneDX (`pyingestkit-cyclonedx.json`).
- **Attestations de provenance :** Preuves de signature cryptographique Sigstore / SLSA provenance générées lors des workflows OIDC GitHub Actions.
- **Traçabilité du déploiement PyPI :** Statut de publication, URL officielle, run ID de workflow de release.
- **Procès-verbal du consommateur public :** Preuve d'installation et de fonctionnement dans un environnement virtuel éphémère vierge depuis l'index public PyPI (`scripts/public_consumer_smoke.py`).

---

## 2. Convention de Nommage des Rapports

```text
YYYY-MM-DD_<version>_distribution-qualification-report.md
```

### Exemple :
- `2026-10-25_v2.2.0_distribution-qualification-report.md`

---

## 3. Modèle de Référence

Pour documenter la publication d'une nouvelle version, dupliquer le modèle standard :
[`TEMPLATE_DIST_REPORT.md`](./TEMPLATE_DIST_REPORT.md).
