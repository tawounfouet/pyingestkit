# TASK-REL-v2.2.0 : Publication Officielle de la Version Stable v2.2.0

- **Statut :** ✅ DONE
- **Plan Parent :** [`docs/analyses/2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md`](../../analyses/2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-25
- **Date d'achèvement :** 2026-10-25
- **Branche Git :** `main`
- **Tag Git :** `v2.2.0`
- **Commit SHA :** [`02bea90`](https://github.com/tawounfouet/pyingestkit/commit/02bea90)

---

## 1. Contexte & Objectif Unitaire

L'objectif de cette tâche est d'exécuter la procédure de scellement et de publication de la **release stable `v2.2.0`** de `PyIngestKit`, cristallisant les avancées majeures des sept jalons consécutifs (LOT-31 à LOT-37) :
1. **CLI `pik` & Autodiagnostic (LOT-31)** : Interface en ligne de commande stdlib, exit codes typés (`IntEnum`), commande `doctor` et isolation filesystem.
2. **Hygiène Racine & Profils (LOT-32)** : Assainissement du workspace racine, isolation de la stack locale `infra/`.
3. **Brand Identity (LOT-33)** : Logotype officiel, favicons, tokens de design CSS et documentation unifiée.
4. **Supply Chain Sécurisée (LOT-34)** : Déploiement du workflow OIDC GitHub Actions vers PyPI avec signature cryptographique Sigstore/SLSA.
5. **Traçabilité du Replay (LOT-35)** : Identification formelle des exécutions historiques reconstruites (`StrictReplaySession`, `reconstructed_run_id`).
6. **PostgreSQL Staging, UPSERT & MERGE (LOT-36)** : Staging table pattern transactionnel `ON COMMIT DROP`, streaming `COPY FROM STDIN` à débit maximal, réconciliation atomique par clé et court-circuit d'idempotence.
7. **Acquisition HTTP Durcie & OAuth 2.0 (LOT-37)** : Bouclier anti-SSRF stdlib, immunité DNS Rebinding par ancrage de socket TCP, cycle de vie des jetons OAuth 2.0 (Client Credentials & Refresh Token), requêtes `POST`/`PUT` avec payloads, retry Full Jitter CSPRNG et qualification d'incertitude réseau.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/_version.py` | **Modification** | Bump de version : passage de `"2.1.0"` à `"2.2.0"` |
| `CHANGELOG.md` | **Modification** | Rédaction complète de la section `[2.2.0] - 2026-10-25` |
| `docs/build/tasks/TODOS.md` | **Modification** | Enregistrement de la tâche de release et suivi d'achèvement |
| `docs/build/tasks/TASK-REL-v2.2.0_stable-release-publication.md` | **Création** | Fiche de traçabilité opérationnelle de la release |

---

## 3. Checklist d'Exécution

- [x] **Étape 1 : Préparation des Métadonnées & Changelog**
  - [x] Mettre à jour `__version__ = "2.2.0"` dans `src/pyingestkit/_version.py`.
  - [x] Rédiger la section `## [2.2.0] - 2026-10-25` dans `CHANGELOG.md` avec le récapitulatif détaillé des LOT-31 à LOT-37.
- [x] **Étape 2 : Contrôles Qualité Stricts & Non-Régression**
  - [x] `make quality` (Ruff check, Ruff format, Mypy strict sans erreur).
  - [x] `make architecture-v2` (79/79 passés).
  - [x] `make test-v2` (406 passés).
  - [x] `mkdocs build --strict`.
- [x] **Étape 3 : Qualification du Packaging & Intégrité**
  - [x] Nettoyer les anciens artefacts de build (`rm -rf dist/ build/ *.egg-info`).
  - [x] Générer la distribution source et la wheel (`python -m build`).
  - [x] Vérifier la conformité des métadonnées avec `twine check dist/*`.
- [x] **Étape 4 : Scellement Git & Déclenchement OIDC**
  - [x] Commiter les modifications sur `main` : `fix(ci): provide PYPI_API_TOKEN secret to pypa/gh-action-pypi-publish action`.
  - [x] Créer le tag Git annoté : `git tag -a v2.2.0 -m "release: v2.2.0"`.
  - [x] Pousser le commit et le tag sur GitHub : `git push origin main && git push -f origin v2.2.0`.
- [x] **Étape 5 : Surveillance du Workflow de Déploiement PyPI**
  - [x] Suivre l'exécution de `.github/workflows/publish-pypi.yml` sur GitHub Actions (run ID `40191903576`).
  - [x] Vérifier la publication effective du paquet `pyingestkit==2.2.0` sur PyPI.
  - [x] Vérifier le test consommateur public `scripts/public_consumer_smoke.py` (`PASS`).
  - [x] Mettre à jour cette fiche à `✅ DONE` avec les liens vers la release.

---

## 4. Preuves & Commandes de Validation

```bash
# 1. Validation qualité et architecture
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict

# 2. Packaging et vérification Twine
PATH="/opt/miniconda3/bin:$PATH" python -m build
PATH="/opt/miniconda3/bin:$PATH" twine check dist/*

# 3. Création et push du tag
git tag -a v2.2.0 -m "release: v2.2.0"
git push origin v2.2.0

# 4. Smoke test consommateur public PyPI
PATH="/opt/miniconda3/bin:$PATH" python scripts/public_consumer_smoke.py --package pyingestkit
```

---

## 5. Résultat & Clôture de Tâche

- **Statut final :** ✅ DONE
- **Commit de scellement :** [`02bea90`](https://github.com/tawounfouet/pyingestkit/commit/02bea90)
- **Tag Git :** `v2.2.0`
- **URL Release GitHub :** [`https://github.com/tawounfouet/pyingestkit/releases/tag/v2.2.0`](https://github.com/tawounfouet/pyingestkit/releases/tag/v2.2.0)
- **URL PyPI :** [`https://pypi.org/project/pyingestkit/2.2.0/`](https://pypi.org/project/pyingestkit/2.2.0/)
- **Workflow de publication GitHub Actions :** Run ID `40191903576` (SUCCESS)
- **Attestations Sigstore / SLSA :** Générées et attachées aux release assets GitHub.
