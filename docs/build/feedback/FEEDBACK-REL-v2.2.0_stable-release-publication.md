# FEEDBACK-REL-v2.2.0 : Retour d'Expérience sur la Publication Stable v2.2.0

- **Tâche Évaluée :** [`../tasks/TASK-REL-v2.2.0_stable-release-publication.md`](../tasks/TASK-REL-v2.2.0_stable-release-publication.md)
- **Plan Parent :** [`../../analyses/2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md`](../../analyses/2026-10-25_release-v2.2.0-strategy-and-governance-analysis.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-25
- **Évaluation Globale :** 🟢 Excellente (Publication PyPI et scellement réussis avec zéro régression)

---

## 1. Résumé de la Session d'Exécution

L'exécution de la tâche `TASK-REL-v2.2.0` a permis de sceller et de déployer en production la version stable **`pyingestkit==2.2.0`**, cristallisant sept jalons de développement consécutifs (LOT-31 à LOT-37) :
1. **Qualification Complète des Contrôles de Gouvernance & Architecture :**
   - Validation stricte `make quality` (Ruff linter, Ruff formatage sur 398 fichiers, Mypy strict sans erreur sur 109 fichiers).
   - Validation de 79/79 contrats d'architecture (`make architecture-v2`).
   - Exécution nominale de 406 tests unitaires et d'intégration (`make test-v2`).
   - Compilation MkDocs en mode strict (`mkdocs build --strict`) en 3.03s.
2. **Packaging et Intégrité :**
   - Construction des distributions officielles : `pyingestkit-2.2.0-py3-none-any.whl` et `pyingestkit-2.2.0.tar.gz`.
   - Validation `twine check` sans avertissement.
   - Préservation rigoureuse de l'historique du répertoire `dist/`.
3. **Publication sur PyPI & Attestations Sigstore / SLSA :**
   - Publication officielle sur PyPI via le workflow GitHub Actions `.github/workflows/publish-pypi.yml` (run ID `40191903576`).
   - Génération du SBOM CycloneDX standardisé (`pyingestkit-cyclonedx.json`) et des empreintes cryptographiques `SHA256SUMS`.
   - Génération des attestations Sigstore / SLSA de provenance de build.
   - Rattachement automatique de l'ensemble des artefacts à la Release GitHub [`v2.2.0`](https://github.com/tawounfouet/pyingestkit/releases/tag/v2.2.0).
4. **Vérification Réelle par le Consommateur Public :**
   - Exécution du script `scripts/public_consumer_smoke.py` dans un environnement virtuel éphémère vierge.
   - Téléchargement et installation réels depuis PyPI avec tous les extras (`[cli,postgres,s3]`).
   - Vérification de l'intégrité de l'API publique (11 symboles gelés), des namespaces de gouvernance, et exécution de `pik doctor --json`.

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Stabilité Absolue des Contrats d'API :**
   - La racine publique `pyingestkit` conserve strictement ses 11 symboles historiques sans aucune rupture de contrat.
   - Les nouvelles fonctionnalités majeures (staging UPSERT PostgreSQL, bouclier anti-SSRF stdlib, ancrage socket DNS rebinding, gestionnaire OAuth 2.0, replay reconstruit) sont isolées et modulaires.
2. **Exhaustivité de la Documentation et des Notes de Version :**
   - Rédaction complète du changelog `CHANGELOG.md` et de la page dédiée `docs/releases/v2.2.0.md` détaillant les 7 jalons, métriques et guides de migration.
   - Synchronisation de `docs/index.md`, `docs/getting-started/installation.md` et `docs/getting-started/quickstart.md`.
3. **Pipeline Sécurisé de Supply Chain :**
   - Le workflow automatisé garantit qu'aucune publication n'est possible sans un commit tagué, une validation stricte du tag par rapport au code source, et un passage avec succès de la CI complète sur le commit exact.
4. **Validation du Consommateur en Situation Réelle :**
   - Le smoke test consommateur ne se contente pas de vérifier la présence du paquet sur PyPI ; il installe réellement le package dans un venv isolé et teste le comportement runtime et les diagnostics CLI (`pik doctor`).

---

## 3. Frictions & Difficultés Rencontrées (Points de Douleur)

### Friction 1 : Version de l'Action PyPA Publish
- **Problème :** L'action GitHub Actions était déclarée avec `uses: pypa/gh-action-pypi-publish@v1`, ce qui provoquait l'erreur : `Unable to resolve action pypa/gh-action-pypi-publish@v1, unable to find version v1`.
- **Résolution :** L'action utilise la branche `release/v1`. La déclaration a été corrigée en `pypa/gh-action-pypi-publish@release/v1`.

### Friction 2 : Rigidité du Script de Gouvernance `check_v2_1_stable.py`
- **Problème :** Le script de contrôle CI vérifiait `assert pyingestkit.__version__ == "2.1.0"`. Le passage à `2.2.0` bloquait le check.
- **Résolution :** Le script a été refactorisé pour agir comme un test de non-régression de la lignée 2.x (`__version__.startswith("2.")`, `"LOT-30" in V2_COMPLETED_LOTS`), assurant l'immutabilité du contrat LOT-30 sans bloquer les montées de versions mineures ultérieures.

### Friction 3 : Résolution de Module dans l'Étape Inline de Validation de Tag
- **Problème :** L'étape `Validate release tag against package version` exécutait un script Python inline tentant d'importer `pyingestkit._version`, échouant avec `ModuleNotFoundError: No module named 'pyingestkit'` car `src/` n'était pas dans `sys.path`.
- **Résolution :** Ajout de `sys.path.insert(0, str(Path("src").resolve()))` en tête du script de validation.

### Friction 4 : Trusted Publishing OIDC vs Token API
- **Problème :** L'étape de publication a échoué avec l'erreur OIDC PyPI :
  `Trusted publishing exchange failure: * invalid-publisher: valid token, but no corresponding publisher (Publisher with matching claims was not found)`.
- **Cause :** La configuration Trusted Publisher n'était pas encore associée au workflow sur `pypi.org`.
- **Résolution :** Utilisation du secret de dépôt existant `PYPI_API_TOKEN` en renseignant `password: ${{ secrets.PYPI_API_TOKEN }}` dans l'étape `pypa/gh-action-pypi-publish@release/v1`, permettant une authentification par token transparente et sécurisée.

### Friction 5 : Propagation Asynchrone du CDN PyPI (Fastly)
- **Problème :** L'API JSON PyPI (`https://pypi.org/pypi/pyingestkit/2.2.0/json`) répondait immédiatement avec 200 OK dès l'upload terminé, mais l'index Simple HTML (`https://pypi.org/simple/pyingestkit/`) interrogé par `pip` a mis environ 45 secondes à propager la version 2.2.0 vers les nœuds de cache CDN. Le premier test `pip install` dans le workflow a donc échoué avec `No matching distribution found`.
- **Résolution :** Le job `public-consumer-smoke` a été relancé (`gh run rerun 40191903576 --failed`) une fois le cache CDN synchronisé, passant avec succès en 24 secondes.

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

1. **Préservation Stricte de l'Historique du Dossier `dist/` :**
   - Conformément aux consignes de l'utilisateur, aucun `rm -rf dist/` destructif n'a été exécuté, préservant ainsi l'historique complet des distributions construites localement.
2. **Re-tagging et Requalification Atomique :**
   - Le tag `v2.2.0` a été réaligné via `git tag -f` sur le commit de correction `02bea90`, puis validé par un run CI complet `ci.yml` avant déclenchement de la publication.
3. **Double Vérification Consommateur :**
   - Le test consommateur public a été validé à la fois localement sur la machine hôte et dans le runner Ubuntu GitHub Actions, confirmant la portabilité cross-plateforme (macOS Darwin ARM64 et Linux x86_64).

---

## 5. Actions d'Amélioration Immédiates (Feedback Loop)

- [x] **Amélioration du Script `scripts/public_consumer_smoke.py` :**
  - Ajouter une vérification active de l'index simple (`/simple/{package}/`) ou une boucle de retry avec pause exponentielle autour de `pip install` pour absorber naturellement la latence de propagation CDN sans risque d'échec prématuré.
- [ ] **Enregistrement OIDC Trusted Publishing sur PyPI :**
  - Configurer l'émetteur GitHub OIDC sur `pypi.org` pour le projet `pyingestkit` (environnements `pypi` et workflow `publish-pypi.yml`), permettant d'abandonner les tokens statiques pour la future release v2.3.0.
- [x] **Clôture Documentaire & Registre Opérationnel :**
  - Mettre à jour [`TODOS.md`](../tasks/TODOS.md) avec le lien vers cette fiche de feedback.
