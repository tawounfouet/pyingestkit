# PyIngestKit Environment Profiles (`envs/`)

Ce dossier regroupe les modèles de profils d'environnement pour PyIngestKit.

## Profils disponibles

| Profil | Modèle | Description | Services requis |
|---|---|---|---|
| **Dev** | `.env.dev.example` | Local-First (fichiers locaux + SQLite) | **Aucun** |
| **Staging** | `.env.stg.example` | Docker Compose (PostgreSQL 16 + MinIO) | PostgreSQL + MinIO |
| **Production** | `.env.prod.example` | PostgreSQL distant + AWS S3 / Cloudflare R2 | PostgreSQL + S3/R2 |

Les fichiers `*.example` sont des **templates de documentation uniquement**. Depuis le contrat V1
B1, le runtime ne les charge jamais automatiquement. Copiez le modèle vers un vrai fichier dotenv
avant utilisation.

```bash
cp envs/.env.dev.example envs/.env.dev
PYINGEST_ENV=dev pyingest config
```

Avec `PYINGEST_ENV=dev`, le CLI cherche, dans le répertoire courant :

```text
envs/.env.dev
.env.dev
```

puis charge `.env`. La priorité est :

```text
variables déjà présentes dans l'OS > dotenv du profil > .env racine
```

`PYINGEST_ENV` sélectionne également `pyingest.yml.<env>`. Si ce fichier YAML n'existe pas, le CLI
échoue explicitement au lieu de retomber silencieusement sur un autre profil.
