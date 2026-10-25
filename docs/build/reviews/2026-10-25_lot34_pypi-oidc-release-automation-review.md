# Revue de Qualification & Clôture Formelle : LOT-34 Automatisation Release PyPI OIDC & Supply Chain

- **Jalon / LOT :** LOT-34 : Automatisation Release PyPI Trusted Publishing, SBOM & Supply Chain
- **Date de la Revue :** 2026-10-25
- **Réviseur / Auditeur :** Thomas Awounfouet / Antigravity
- **Statut de Clôture :** ✅ **APPROUVÉ POUR MERGE & RELEASE**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-release-automation-and-supply-chain.md`](../plans/2026-10-24_plan-release-automation-and-supply-chain.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-004_pypi-supply-chain-and-release-automation.md`](../backlog/ITEM-004_pypi-supply-chain-and-release-automation.md)
- **Branche :** `feat/pypi-oidc-release-automation`

---

## 1. Résumé Exécutif & Périmètre Livré

Le lot **LOT-34** a déployé l'infrastructure de publication continue et de sécurisation de la chaîne d'approvisionnement logicielle (*Software Supply Chain*) pour PyIngestKit au standard de pointe :
1. **PyPI Trusted Publishing (OIDC)** : Remplacement des secrets statiques par l'échange cryptographique OIDC natif entre GitHub Actions et PyPI (`pypa/gh-action-pypi-publish@v1`), orchestré dans `.github/workflows/publish-pypi.yml`.
2. **SBOM Standardisé CycloneDX & SHA-256** : Génération systématique de l'inventaire des composants `pyingestkit-cyclonedx.json` et des empreintes vérifiables `SHA256SUMS` rattachés à la Release GitHub.
3. **Attestations Cryptographiques Sigstore (SLSA)** : Signature automatique de la provenance des builds via `actions/attest-build-provenance@v2`.
4. **Smoke Test Consommateur Public Post-Release** : Script autonome `scripts/public_consumer_smoke.py` vérifiant la propagation PyPI, l'installation sans cache dans un virtualenv isolé, les 11 symboles de l'API publique racine gelée et les diagnostics `pik doctor --json`.
5. **Gouvernance Git & Invariants RFC-001** : Création de `.github/pull_request_template.md` pour verrouiller les invariants de publication CAS, ledgers, holds, GC et contrats wire.
6. **Optimisation des performances CI** : Filtrage du déclencheur `push` sur `branches: [main]` dans `.github/workflows/ci.yml` (suppression des doubles runs CI sur les PRs) et activation globale de `cache: pip`.
7. **Métadonnées PEP 621** : Déclaration de la section `[project.urls]` dans `pyproject.toml`.

---

## 2. Grille d'Audit de Conformité

| Domaine d'Audit | Critère Vérifié | Évaluation | Preuve / Observation |
| :--- | :--- | :--- | :--- |
| **Gouvernance PR** | `.github/pull_request_template.md` présent et structuré | Conforme ✅ | Invariants RFC-001 et checklists inclus |
| **Optimisation CI** | `ci.yml` filtré sur `main` + `cache: pip` activé sur les 26 étapes | Conforme ✅ | Syntax validée sans erreurs |
| **Workflow de Release** | `publish-pypi.yml` configuré OIDC + SBOM + Sigstore + Release Assets | Conforme ✅ | YAML syntaxe vérifiée et validée |
| **Smoke Consommateur** | `scripts/public_consumer_smoke.py` passe sur wheel réel | Conforme ✅ | `{"public_consumer_smoke": "PASS"}` validé en venv isolé |
| **Modularité CLI** | `src/pyingestkit/cli/__main__.py` présent | Conforme ✅ | `python -m pyingestkit.cli doctor --json` fonctionnel |
| **Métadonnées PEP 621** | `[project.urls]` configuré dans `pyproject.toml` | Conforme ✅ | Validé par `tomllib` |
| **Architecture Hexagonale** | 79 tests d'architecture verts sans violation de frontières | Conforme ✅ | `make architecture-v2` 100% vert (1.34s) |
| **Qualité & Typage** | Zéro avertissement Ruff et Mypy | Conforme ✅ | 104 fichiers source conformes (`make quality`) |
| **Non-Régression Globale** | 367 tests unitaires, conformité et intégration verts | Conforme ✅ | `make test-v2` validé (4.20s) |
| **Documentation Stricte** | `mkdocs build --strict` compile sans warning | Conforme ✅ | Build validé en 2.67s |

---

## 3. Points d'Arbitrage Validés

1. **Parité avec `pytransformkit` :** Reprise des mécanismes d'attestation de provenance Sigstore et du pattern de vérification consommateur public post-PyPI.
2. **Installation complète des extras dans le smoke test :** `[cli,postgres,s3]` est requis pour valider non seulement les bibliothèques coeur et les connecteurs, mais également la commande `pik doctor`.
3. **Double point d'entrée CLI :** Support transparent à la fois du script console `pik` et de l'invocation modulaire `python -m pyingestkit.cli`.

---

## 4. Dettes Techniques Résiduelles & Évolutions Futures

- Configuration one-off requise sur l'interface PyPI pour lier l'environnement GitHub Actions `pypi` (Trusted Publisher).
- *Évolution suivante :* LOT-35 (`ITEM-005`) — Service de reconstruction historique et audit de provenance RAW.

---

## 5. Décision Formelle de Livraison

La conformité technique, sécuritaire et opérationnelle du lot est **validée sans réserve**.
- [x] Fusion autorisée vers la branche principale (`main`).
- [x] Clôture du lot LOT-34 validée.
