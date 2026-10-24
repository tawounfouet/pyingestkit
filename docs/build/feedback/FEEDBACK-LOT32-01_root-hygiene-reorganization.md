# FEEDBACK-LOT32-01 : Retour d'Expérience sur l'Assainissement de la Racine du Package

- **Tâche Évaluée :** [`../tasks/TASK-LOT32-01_root-hygiene-and-profile-reorganization.md`](../tasks/TASK-LOT32-01_root-hygiene-and-profile-reorganization.md)
- **Plan Parent :** [`../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md`](../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md)
- **Auteur(s) du REX :** Antigravity / AWF
- **Date du REX :** 2026-10-24
- **Évaluation Globale :** 🟢 Excellente (Exécution rapide et validation sans régression)

---

## 1. Résumé de la Session d'Exécution

L'exécution de la tâche `TASK-LOT32-01` a permis de réduire la racine de `PyIngestKit` de **38 à 23 entrées** :
- Déplacement des 6 profils YAML applicatifs dans `examples/configs/`.
- Déplacement de la stack Docker locale et des templates d'environnements dans `infra/`.
- Archivage du checksum historique `SHA256SUMS-v0.2.0.txt` dans `docs/releases/archive/`.
- Validation complète des 367 tests unitaires, 79 tests d'architecture et 76 tests de contrat.
- Commit conventionnel scellé : `2fbad5b`.

---

## 2. Ce Qui a Bien Fonctionné (Points Forts)

1. **Isolation parfaite des tests de contrat :**
   Les tests `tests/contract/test_v1_stability_policy.py` utilisaient déjà `tmp_path` et `monkeypatch.chdir()`. Aucun test ne dépendait des fichiers YAML physiques de la racine, garantissant une migration avec **zéro régression**.
2. **Utilisation de `git mv` :**
   Tous les fichiers ont été déplacés avec leur historique complet préservé (100 % rename detection dans Git).
3. **Vérification rapide via `Makefile` :**
   Les commandes `make architecture-v2` et `make contract-v2` ont permis de valider les invariants en moins de 2 secondes.

---

## 3. Frictions & Points d'Attention

- **Protection Git des environnements :**
  Le fichier `.gitignore` contenait initialement des règles statiques ciblant `envs/.env*`. Lors du déplacement vers `infra/envs/`, il a été nécessaire de mettre à jour immédiatement `.gitignore` pour éviter toute fuite involontaire de variables d'environnement locales (`infra/envs/.env*`).

---

## 4. Arbitrages & Décisions Prises en Cours de Vol

- **Arbitrage de nommage du dossier d'infrastructure :**
  - *Proposition initiale :* `deployment/`
  - *Intervention du développeur :* Proposition d'utiliser le nom plus court et plus standard **`infra/`**.
  - *Décision retenue :* **`infra/`**
  - *Justification :* Le dossier contient une stack d'infrastructure locale de test (PostgreSQL 16 + MinIO S3) et des modèles de configurations d'environnements, ce qui relève de l'infrastructure d'exécution et non du déploiement applicatif final. Cela aligne également le package avec la convention globale du workspace racine (`/Users/awf/workspace/infra/`).

---

## 5. Actions d'Amélioration Immédiates (Feedback Loop)

- [x] **Mise à jour immédiate de `.gitignore` :** Intégration de `infra/envs/.env*` et `!infra/envs/.env*.example`.
- [x] **Mise à jour des guides :** Correction de [`docs/guides/v1-production-pilot.md`](../../guides/v1-production-pilot.md) pour pointer vers `docker compose -f infra/docker-compose.staging.yml up -d`.
- [x] **Enseignement pour les tâches futures :** Toujours vérifier les règles de `.gitignore` lors du déplacement d'un répertoire sensible ou contenant des `.env`.
