# ITEM-002 : Assainissement de la Racine du Dépôt & Réorganisation des Profils YAML

- **Statut :** PLANNED
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** HAUTE
- **Composant Cible :** Structure du Repository / Packaging
- **Analyse Associée :** [`docs/analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md`](../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md)
- **LOT Cible :** LOT-32

---

## 1. Contexte & Problématique Constatée

La racine du dépôt compte actuellement **38 entrées**, encombrée par :
- 6 fichiers YAML de configuration applicative (`pyingest.yml`, `pyingest.yml.dev`, etc.).
- 1 fichier de stack locale `docker-compose.staging.yml`.
- 1 dossier `envs/`.
- 1 empreinte obsolète `SHA256SUMS-v0.2.0.txt`.

En comparaison, [`pytransformkit`](../../../../pytransformkit) compte 25 entrées épurées et zéro fichier YAML loose à la racine.

---

## 2. Expression du Besoin & User Story

- **En tant que :** Développeur, contributeur open-source ou auditeur de code.
- **Je souhaite :** Une racine de dépôt canonique, sans configurations applicatives loose ni résidus de tests.
- **Afin de :** Présenter une arborescence professionnelle, réduire la surcharge cognitive et éviter toute fuite de fichiers dans les archives `sdist`.

---

## 3. Bénéfices Attendus

1. **Hygiène du code :** Racine réduite de 38 à 22 entrées.
2. **Alignement écosystème :** Rangement standardisé des exemples de profils dans `examples/configs/` et de l'infra dans `deployment/`.
3. **Sécurité :** Zéro fichier d'environnement sensible risquant d'être commité ou packagé.

---

## 4. Invariants Architecturaux

- [x] Zéro impact sur les suites de tests contractuelles (`tests/contract/fixtures/`) qui tournent sous `tmp_path`.
- [x] Respect des mécanismes de résolution de configuration (`PYINGEST_CONFIG` et `--config`).

---

## 5. Livrables Associés

- Tâche d'exécution : [`docs/build/tasks/TASK-LOT32-01_root-hygiene-and-profile-reorganization.md`](../tasks/TASK-LOT32-01_root-hygiene-and-profile-reorganization.md)
