# TASK-LOT32-01 : Assainissement de la Racine & Migration des Configurations Applicatives

- **Statut :** 📋 **TODO**
- **Plan Parent :** [`docs/analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md`](../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Branche Git :** `feat/root-cleanup-and-backlog-governance`

---

## 1. Contexte & Objectif Unitaire

Assainir la racine de [`PyIngestKit`](../../../README.md) pour la faire passer de **38 à 22 entrées**, conformément aux standards éprouvés sur `pytransformkit` (25 entrées) et `pyworkflowkit` (31 entrées).

Objectifs techniques :
1. **Zéro configuration YAML applicative à la racine** : Déplacer les 6 fichiers de configuration (`pyingest*.yml`) dans `examples/configs/`.
2. **Infrastructure de test isolée** : Déplacer `docker-compose.staging.yml` et le dossier `envs/` dans un dossier dédié `deployment/`.
3. **Archivage historique** : Déplacer le résidu de signature `SHA256SUMS-v0.2.0.txt` dans `docs/releases/archive/`.
4. **Nettoyage système** : Éliminer les résidus `.DS_Store` locaux.

---

## 2. Périmètre des Fichiers

| Fichier Initial (Racine) | Action | Destination Cible |
| :--- | :--- | :--- |
| `pyingest.yml` | `git mv` | `examples/configs/pyingest.yml` |
| `pyingest.yml.dev` | `git mv` | `examples/configs/pyingest.yml.dev` |
| `pyingest.yml.stg` | `git mv` | `examples/configs/pyingest.yml.stg` |
| `pyingest.yml.prod` | `git mv` | `examples/configs/pyingest.yml.prod` |
| `pyingest.yml.example` | `git mv` | `examples/configs/pyingest.yml.example` |
| `pyingest-s3.example.yml` | `git mv` | `examples/configs/pyingest-s3.example.yml` |
| `docker-compose.staging.yml` | `git mv` | `deployment/docker-compose.staging.yml` |
| `envs/` | `git mv` | `deployment/envs/` |
| `SHA256SUMS-v0.2.0.txt` | `git mv` | `docs/releases/archive/SHA256SUMS-v0.2.0.txt` |
| `.DS_Store` | `rm` | Supprimé du filesystem |

---

## 3. Checklist d'Exécution

- [ ] Créer les dossiers de destination :
  - [ ] `mkdir -p examples/configs`
  - [ ] `mkdir -p deployment`
  - [ ] `mkdir -p docs/releases/archive`
- [ ] Déplacer les configurations YAML avec `git mv`.
- [ ] Déplacer l'infrastructure Docker et les templates d'environnements avec `git mv`.
- [ ] Archiver l'empreinte historique V0.2.0 avec `git mv`.
- [ ] Mettre à jour les références documentaires :
  - [ ] [`docs/guides/v1-production-pilot.md`](../../guides/v1-production-pilot.md)
  - [ ] [`docs/reviews/v0.6.0-multienv-profiles-and-s3-object-storage-review.md`](../../reviews/v0.6.0-multienv-profiles-and-s3-object-storage-review.md)
- [ ] Exécuter les suites de tests contractuelles et unitaires pour certifier l'absence d'impact.
- [ ] Commiter le nettoyage avec un message conventionnel : `refactor(repo): reorganize root directory, yaml profiles, and staging infra`.

---

## 4. Preuves & Commandes de Validation

```bash
# Vérification que le contrat de stabilité ne dépend pas des fichiers racine
PATH="/opt/miniconda3/bin:$PATH" make contract-v2

# Vérification de l'ensemble de la suite
PATH="/opt/miniconda3/bin:$PATH" make test-v2

# Comptage des entrées de la racine (doit être <= 23)
ls -la | grep -v '^total' | wc -l
```
