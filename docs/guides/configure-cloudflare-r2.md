# Guide : Configuration et Intégration de Cloudflare R2 Object Storage avec PyIngestKit V0.6.0

## Présentation

**PyIngestKit V0.6.0** prend en charge le stockage d'artéfacts durables (payloads bruts RAW, rapports de validation, de profilage, diffs, snapshots de version et manifests d'exécution) dans un stockage d'objets S3-compatible distant comme **[Cloudflare R2 Object Storage](https://dash.cloudflare.com/r2)**.

Ce guide détaille pas à pas la configuration et l'exécution d'un pipeline complet liant **Cloudflare R2** (artéfacts), **PostgreSQL** (métadonnées d'exécution) et **PostgreSQL** (données cibles).

---

## Étape 1 : Récupération des Identifiants Cloudflare R2

Depuis le tableau de bord Cloudflare R2 (section **Account Details** / **Manage R2 API Tokens**) :
- **Account ID** : `<votre_account_id>`
- **S3 API Endpoint** : `https://<votre_account_id>.r2.cloudflarestorage.com`
- **Access Key ID** : `<votre_access_key_id>`
- **Secret Access Key** : `<votre_secret_access_key>`

---

## Étape 2 : Installation des Dépendances S3 (`boto3`)

Dans l'environnement virtuel du projet :

```bash
pip install -e ".[s3,postgres]"
```

---

## Étape 3 : Configuration du Fichier `.env` Local

Renseignez les variables d'environnement dans votre fichier [`.env`](../../.env.example) :

```env
# Variables d'environnement pour Cloudflare R2 Object Storage (API S3)
AWS_ACCESS_KEY_ID=your_cloudflare_r2_access_key_id
AWS_SECRET_ACCESS_KEY=your_cloudflare_r2_secret_access_key
AWS_DEFAULT_REGION=auto
PYINGEST_S3_ENDPOINT_URL=https://<votre_account_id>.r2.cloudflarestorage.com

# DSN PostgreSQL (Métadonnées & Target)
PYINGEST_TARGET_DATABASE_URL=postgresql://postgres@localhost:5432/pyingest
PYINGEST_DATABASE_URL=postgresql://postgres@localhost:5432/pyingest
```

---

## Étape 4 : Fichier de Configuration YAML (`demo-versioned-s3.yml`)

Configurez le fichier YAML de votre job (voir exemple [`demo-versioned-s3.yml`](../../examples/plugin_package/demo-versioned-s3.yml)) :

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: true
  parameters:
    target_id: postgres.demo.versioned_s3
    target_schema: public
    target_table: pyingestkit_demo_versioned_s3
    target_dsn_env: PYINGEST_TARGET_DATABASE_URL
    metadata_backend: postgres
    metadata_dsn_env: PYINGEST_DATABASE_URL

# Stockage d'artéfacts sur Cloudflare R2
artifacts:
  backend: s3
  s3:
    bucket: pyingest-artifacts
    prefix: demo/versioned-s3
    region_name: auto
    endpoint_url_env: PYINGEST_S3_ENDPOINT_URL

# Stockage des métadonnées d'exécution sur PostgreSQL
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL

logging:
  level: INFO
  format: rich
  console: false
  file:
    enabled: false
```

---

## Étape 5 : Exécution du Pipeline avec la CLI `pyingest`

1. Préparez la table de destination dans PostgreSQL :
   ```bash
   psql -U postgres -d pyingest -c "CREATE TABLE IF NOT EXISTS pyingestkit_demo_versioned_s3 (id BIGINT PRIMARY KEY, name TEXT NOT NULL, score DOUBLE PRECISION NOT NULL);"
   ```

2. Exécutez l'ingestion (Révision 1) :
   ```bash
   pyingest run demo.versioned_postgres \
     --config examples/plugin_package/demo-versioned-s3.yml \
     --param revision=1
   ```

   **Résultat :**
   ```text
   ╭────────────── PyIngestKit Run ───────────────╮
   │ SUCCESS  demo.versioned_postgres             │
   │ run_id: 6cba2d20-dcf6-42c1-9cbf-f518419afe2c │
   │ duration: 1.357s                             │
   ╰──────────────────────────────────────────────╯
   ```

3. Exécutez la mise à jour (Révision 2) :
   ```bash
   pyingest run demo.versioned_postgres \
     --config examples/plugin_package/demo-versioned-s3.yml \
     --param revision=2
   ```

---

## Étape 6 : Inspection et Validation des Données

### 1. Sur Cloudflare R2 (Stockage d'objets)
Les objets suivants sont automatiquement synchronisés dans le bucket `pyingest-artifacts` :
- `demo/versioned-s3/runs/.../raw/versioned-postgres-people.ndjson`
- `demo/versioned-s3/runs/.../reports/validation.json`
- `demo/versioned-s3/runs/.../reports/profile.json`
- `demo/versioned-s3/runs/.../reports/diff.json`
- `demo/versioned-s3/runs/.../manifest.json`

### 2. Dans PostgreSQL (Base de métadonnées et données cibles)
- **Données cibles :** `SELECT * FROM pyingestkit_demo_versioned_s3;`
- **Historique des exécutions :** `SELECT run_id, job_id, status, duration_seconds FROM runs;`
- **Chargements cibles :** `SELECT load_id, target_id, rows_loaded, mode, status FROM target_loads;`
