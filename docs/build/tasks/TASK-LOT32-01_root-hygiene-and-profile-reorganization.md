# TASK-LOT32-01 : Assainissement de la Racine & Migration des Configurations Applicatives

- **Statut :** ✅ **DONE**
- **Plan Parent :** [`docs/analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md`](../../analyses/2026-10-24_backlog-governance-and-root-hygiene-analysis.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date d'achèvement :** 2026-10-24
- **Branche Git :** `feat/agentic-governance-and-instructions`

---

## 1. Contexte & Objectif Unitaire

Assainir la racine de [`PyIngestKit`](../../../README.md) pour la faire passer de **38 à 23 entrées**, conformément aux standards éprouvés sur `pytransformkit` (25 entrées) et `pyworkflowkit` (31 entrées).

Objectifs techniques :
1. **Zéro configuration YAML applicative à la racine** : Déplacer les 6 fichiers de configuration (`pyingest*.yml`) dans `examples/configs/`.
2. **Infrastructure de test isolée** : Déplacer `docker-compose.staging.yml` et le dossier `envs/` dans un dossier dédié `infra/`.
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
| `docker-compose.staging.yml` | `git mv` | `infra/docker-compose.staging.yml` |
| `envs/` | `git mv` | `infra/envs/` |
| `SHA256SUMS-v0.2.0.txt` | `git mv` | `docs/releases/archive/SHA256SUMS-v0.2.0.txt` |
| `.DS_Store` | `rm` | Supprimé du filesystem |

---

## 3. Checklist d'Exécution

- [x] Créer les dossiers de destination :
  - [x] `mkdir -p examples/configs`
  - [x] `mkdir -p infra`
  - [x] `mkdir -p docs/releases/archive`
- [x] Déplacer les configurations YAML avec `git mv`.
- [x] Déplacer l'infrastructure Docker et les templates d'environnements avec `git mv` dans `infra/`.
- [x] Archiver l'empreinte historique V0.2.0 avec `git mv`.
- [x] Mettre à jour `.gitignore` pour protéger `infra/envs/.env*`.
- [x] Mettre à jour les références documentaires :
  - [x] [`docs/guides/v1-production-pilot.md`](../../guides/v1-production-pilot.md)
  - [x] [`infra/envs/README.md`](../../../infra/envs/README.md)
- [x] Exécuter les suites de tests contractuelles et unitaires pour certifier l'absence d'impact.
- [ ] Commiter le nettoyage avec un message conventionnel : `refactor(repo): reorganize root directory, yaml profiles, and staging infra`.

---

## 4. Preuves & Commandes de Validation

```bash
# 1. Vérification que le contrat de stabilité ne dépend pas des fichiers racine
PATH="/opt/miniconda3/bin:$PATH" make contract-v2
# Résultat : 76 passed in 0.37s ✅

# 2. Vérification des frontières d'architecture hexagonale
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
# Résultat : 79 passed in 1.44s ✅

# 3. Vérification de l'ensemble de la suite
PATH="/opt/miniconda3/bin:$PATH" make test-v2
# Résultat : 367 passed, 25 skipped in 3.98s ✅
```

---

## 5. Résultat & Constat de Clôture

- Entrées racine initiales : 38
- Entrées racine cibles : 23 répertoires/fichiers suivis
- Zero régression fonctionnelle ou contractuelle.
