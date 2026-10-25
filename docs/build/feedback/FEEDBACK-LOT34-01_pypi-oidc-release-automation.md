# FEEDBACK-LOT34-01 : Automatisation Release PyPI OIDC & Supply Chain

- **Tâche Évaluée :** [`../tasks/TASK-LOT34-01_pypi-oidc-release-automation.md`](../tasks/TASK-LOT34-01_pypi-oidc-release-automation.md)
- **Plan Parent :** [`../plans/2026-10-24_plan-release-automation-and-supply-chain.md`](../plans/2026-10-24_plan-release-automation-and-supply-chain.md)
- **Item Backlog :** [`../backlog/ITEM-004_pypi-supply-chain-and-release-automation.md`](../backlog/ITEM-004_pypi-supply-chain-and-release-automation.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-25
- **Évaluation Globale :** 🟢 Excellente

---

## 1. Résumé de la Session d'Exécution

L'exécution de la tâche a permis d'implémenter l'ensemble des mécanismes de supply chain sécurisée et d'automatisation de publication pour PyIngestKit :
1. **Pull Request Template d'Architecture** : Création de `.github/pull_request_template.md` verrouillant les invariants architecturaux (RFC-001, CAS, ledgers durables, holds, GC sécurisé, gouvernance de rollback et contrats wire).
2. **Optimisation CI & Caching** : Modification de `.github/workflows/ci.yml` pour restreindre les déclencheurs de `push` à la branche `main` (évite les doubles exécutions redondantes sur les PRs) et ajout systématique de `cache: pip` sur l'ensemble des 26 étapes Python.
3. **Workflow OIDC & Supply Chain** : Création de `.github/workflows/publish-pypi.yml` avec support PyPI Trusted Publishing (OIDC sans token statique), génération standardisée de SBOM CycloneDX (`cyclonedx-py`), calcul des empreintes `SHA256SUMS`, attestations cryptographiques Sigstore (`actions/attest-build-provenance@v2`), et rattachement des assets à la Release GitHub.
4. **Script Consommateur Public Post-Release** : Création de `scripts/public_consumer_smoke.py` autonome pour attendre la propagation PyPI, instancier un virtualenv vierge, installer la distribution publiée avec extras, et valider l'intégrité de l'API publique (11 symboles gelés), les namespaces de gouvernance, et les diagnostics `pik doctor`.
5. **Métadonnées PEP 621** : Enrichissement de `pyproject.toml` avec la section `[project.urls]` (`Homepage`, `Documentation`, `Repository`, `Changelog`, `Issues`).

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Parité avec les packages frères (`pytransformkit`) :** Les patterns éprouvés d'authentification sans secret (Trusted Publishing) et de test consommateur post-publication ont été repris et adaptés avec succès.
2. **Smoke Test Réel en Environnement Isolé :** Le test du script `public_consumer_smoke.py` a été exécuté sur un wheel réel (`pyingestkit-2.1.0-py3-none-any.whl`), validant l'installation dans un venv temporaire, le check des dépendances (`pip check`) et l'autodiagnostic (`pik doctor --json`).
3. **Zéro Régression de Qualité & Architecture :** L'ensemble des suites `make quality`, `make architecture-v2` (79/79) et `make test-v2` (367/367) sont passées avec succès.

---

## 3. Frictions & Difficultés Rencontrées (Points de Douleur)

- **Extra CLI pour `pik doctor` dans l'environnement consommateur :** Le premier jet de `public_consumer_smoke.py` installait `[postgres,s3]`, ce qui laissait les dépendances CLI `typer` et `rich` manquantes. Le script a été ajusté pour installer `[cli,postgres,s3]`, permettant à `pik doctor` d'émettre son statut `healthy` complet.
- **Typo sur le nom d'argument argparse :** L'option `--skip-pypi-wait` produit l'attribut Python `args.skip_pypi_wait` (avec underscore). Une soustraction involontaire `args.skip_pypi - wait` a été détectée et corrigée immédiatement lors des tests.

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

- **Ajout de `src/pyingestkit/cli/__main__.py` :** Permet d'exécuter la CLI non seulement via le binaire `pik`, mais aussi directement via `python -m pyingestkit.cli`, assurant une parité parfaite en mode conteneurisé ou virtualisé.
- **Assertions strictes sur le schéma de sortie de `pik doctor` :** Le smoke test vérifie explicitement `doctor_json["status"] in ("healthy", "degraded", "unhealthy")` et `doctor_json["pyingestkit"]["version"] == expected_version`.

---

## 5. Leçons Apprises & Actions pour la Suite

1. **Vérification automatique de l'existence des wheels :** Toujours vérifier les chemins d'importation réels des modules avant d'écrire les assertions de smoke tests (`pyingestkit.governance.rollback` pour `GovernedRollbackService`).
2. **Prochaine étape :** Mettre à jour `TASK-LOT34-01` et `TODOS.md` à `DONE`, rédiger la revue de lot formelle, et soumettre la PR vers `main`.
