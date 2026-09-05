# PyIngestKit Environment Profiles (`envs/`)

Ce dossier regroupe les profils d'environnement pour PyIngestKit.

## Profils disponibles

| Profil | Fichier | Description | Services requis |
|---|---|---|---|
| **Dev** | `.env.dev.example` / `.env.dev` | Local-First (fichiers locaux + SQLite) | **Aucun** |
| **Staging** | `.env.stg.example` | Docker Compose (PostgreSQL 16 + MinIO) | `docker compose -f docker-compose.staging.yml up -d` |
| **Production** | `.env.prod.example` | Production managée (PostgreSQL distant + AWS S3 / Cloudflare R2) | Base PostgreSQL + Bucket S3 / R2 |

## Activation rapide

Pour activer un environnement à la racine du projet :

```bash
# Activer le profil Développement :
cp envs/.env.dev .env

# Activer le profil Staging :
cp envs/.env.stg.example .env

# Activer le profil Production :
cp envs/.env.prod.example .env
```

Alternativement, vous pouvez utiliser la variable `PYINGEST_ENV` :
```bash
PYINGEST_ENV=dev pyingest runs
```
