# TASK-LOT34-01 : Automatisation Release PyPI OIDC & Supply Chain

- **Statut :** ✅ DONE
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-release-automation-and-supply-chain.md`](../plans/2026-10-24_plan-release-automation-and-supply-chain.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-004_pypi-supply-chain-and-release-automation.md`](../backlog/ITEM-004_pypi-supply-chain-and-release-automation.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date d'achèvement :** 2026-10-25
- **Branche Git :** `feat/pypi-oidc-release-automation`

---

## 1. Contexte & Objectif Unitaire

Automatiser la publication des releases sur PyPI et sécuriser la chaîne d'approvisionnement (*Software Supply Chain*) :
1. Remplacer les tokens API manuels par **PyPI Trusted Publishing (OIDC)** dans `.github/workflows/publish-pypi.yml`.
2. Générer automatiquement un SBOM standardisé **CycloneDX** et les empreintes **SHA256SUMS**.
3. Signer les artefacts de distribution avec des attestations cryptographiques **Sigstore**.
4. Déclencher le workflow sur événement GitHub Release (`types: [published]`) ou par `workflow_dispatch` d'un tag qualifié.
5. Créer le script autonome de test consommateur post-release `scripts/public_consumer_smoke.py`.
6. Mettre en place `.github/pull_request_template.md` pour verrouiller les invariants d'architecture.
7. Optimiser la CI dans `.github/workflows/ci.yml` (filtrage `branches: [main]` pour push et cache pip).
8. Enrichir `pyproject.toml` avec les `[project.urls]` PEP 621.

---

## 2. Périmètre des Fichiers

### Créations
- `.github/workflows/publish-pypi.yml` (Workflow de publication OIDC + SBOM + Sigstore)
- `.github/pull_request_template.md` (Gabarit PR de gouvernance d'architecture)
- `scripts/public_consumer_smoke.py` (Script de test consommateur après publication)
- `src/pyingestkit/cli/__main__.py` (Point d'entrée modulaire pour `python -m pyingestkit.cli`)

### Modifications
- `.github/workflows/ci.yml` (Filtrage des déclencheurs et cache pip)
- `pyproject.toml` (Section `[project.urls]` PEP 621)
- `docs/build/tasks/TODOS.md` (Mise à jour du statut)

---

## 3. Checklist d'Exécution

- [x] **Étape 1 :** Créer le template de Pull Request `.github/pull_request_template.md`.
- [x] **Étape 2 :** Optimiser `.github/workflows/ci.yml` (push filtré sur `main` et cache pip).
- [x] **Étape 3 :** Créer le workflow GitHub Actions `.github/workflows/publish-pypi.yml`.
- [x] **Étape 4 :** Créer le script autonome `scripts/public_consumer_smoke.py`.
- [x] **Étape 5 :** Mettre à jour `pyproject.toml` avec `[project.urls]`.
- [x] **Étape 6 :** Valider la syntaxe des workflows, scripts et configurations (`make quality`, `make architecture-v2`, `make test-v2`, `mkdocs build --strict`).
- [x] **Étape 7 :** Rédiger la fiche de REX `FEEDBACK-LOT34-01` et la revue formelle de lot.

---

## 4. Preuves & Commandes de Validation

```bash
# Vérification syntaxique du script de smoke
PATH="/opt/miniconda3/bin:$PATH" python scripts/public_consumer_smoke.py --help

# Validation du test consommateur dans un venv isolé sur wheel réel
PATH="/opt/miniconda3/bin:$PATH" python scripts/public_consumer_smoke.py --wheel dist/pyingestkit-2.1.0-py3-none-any.whl
# {"public_consumer_smoke": "PASS", "package": "pyingestkit", "version": "2.1.0", "python": "3.13.12", "platform": "darwin"}

# Validation qualité et architecture
PATH="/opt/miniconda3/bin:$PATH" make quality             # All checks passed, 104 source files checked
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2    # 79 passed in 1.34s
PATH="/opt/miniconda3/bin:$PATH" make test-v2            # 367 passed, 25 skipped in 4.20s
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict   # Documentation built in 2.67 seconds
```

---

## 5. Résultat & Clôture de Tâche

- **Commit SHA :** Prêt pour commit et livraison PR
- **Statut final :** ✅ DONE
- **Fiche REX associée :** [`../feedback/FEEDBACK-LOT34-01_pypi-oidc-release-automation.md`](../feedback/FEEDBACK-LOT34-01_pypi-oidc-release-automation.md)
