# Guide de Déploiement sur PyPI - PyIngestKit

Ce guide récapitule toutes les étapes suivies pour configurer, vérifier, construire et publier le package officiel **`pyingestkit`** sur PyPI ([Python Package Index](https://pypi.org/project/pyingestkit/)).

---

## 1. Prérequis & Compte PyPI

1. **Compte PyPI** : Disposer d'un compte sur [pypi.org](https://pypi.org/).
2. **Jeton d'API (API Token)** :
   - Accéder à **Account Settings > API tokens** (Paramètres du compte > Jetons d'API).
   - Générer un jeton global pour la première publication (ou restreint au projet `pyingestkit` pour les versions suivantes).
   - Copier la clé générée (`pypi-...`).

---

## 2. Vérification du Nom sur PyPI

Le nom du package est unique au niveau mondial sur PyPI :
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/pyingestkit/json
```
*Le code retourné `404` confirme que le nom `pyingestkit` est disponible et prêt à être revendiqué lors de la première publication.*

---

## 3. Configuration du Projet (`pyproject.toml`)

Le fichier [`pyproject.toml`](pyproject.toml) intègre les métadonnées modernes, les URLs de navigation et la classification de production :

```toml
[build-system]
requires = ["setuptools>=77", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyingestkit"
dynamic = ["version"]
description = "Composable ingestion tooling for Python."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
license-files = ["LICENSE"]
authors = [{ name = "Thomas Awounfouet" }]

classifiers = [
  "Development Status :: 5 - Production/Stable",
  "Intended Audience :: Developers",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Topic :: Software Development :: Libraries :: Python Modules",
]

[project.urls]
Homepage = "https://github.com/tawounfouet/pyingestkit"
Documentation = "https://github.com/tawounfouet/pyingestkit#readme"
Repository = "https://github.com/tawounfouet/pyingestkit"
Issues = "https://github.com/tawounfouet/pyingestkit/issues"
Changelog = "https://github.com/tawounfouet/pyingestkit/releases"

[project.scripts]
pyingest = "pyingestkit.cli.main:main"
```

---

## 4. Sécurisation des Identifiants (`.env`)

Pour éviter tout commit involontaire de jeton API sur Git :

1. Le fichier `.env` est exclu dans [`.gitignore`](.gitignore) :
   ```env
   .env
   .env.*
   !.env*.example
   ```
2. Créez un fichier `.env` à la racine du projet avec vos identifiants :
   ```env
   TWINE_USERNAME=__token__
   TWINE_PASSWORD=pypi-VOTRE_JETON_API_ICI
   ```
3. Le fichier modèle [`.env.example`](.env.example) documente les variables requises.

---

## 5. Déploiement Local via `Makefile`

Le [`Makefile`](Makefile) inclut automatiquement `.env` et propose deux cibles dédiées :

```bash
# 1. Vérifier la conformité du build sans publier
make publish-check

# 2. Nettoyer, construire et publier sur PyPI
make publish
```

---

## 6. Déploiement Manuel Étape par Étape

Pour exécuter manuellement chaque étape dans le terminal :

### Étape 6.1 : Nettoyer et construire les distributions
```bash
rm -rf build dist *.egg-info src/*.egg-info
python -m build
```
*Génère le wheel (`.whl`) et l'archive source (`.tar.gz`) dans `dist/`.*

### Étape 6.2 : Vérifier la conformité des artefacts
```bash
python -m twine check dist/*
```
*Doit afficher `PASSED` pour chaque distribution.*

### Étape 6.3 : Téléverser sur PyPI
```bash
export $(cat .env | xargs)
python -m twine upload dist/pyingestkit-*
```

---

## 7. Déploiement Automatisé via GitHub Actions

Le workflow [`.github/workflows/publish.yml`](.github/workflows/publish.yml) permet de publier automatiquement :
- Lors de la publication d'une Release GitHub (`release: types: [published]`).
- Manuellement via déclencheur à la demande (`workflow_dispatch`).

### Configuration du Secret GitHub
Le secret de dépôt `PYPI_API_TOKEN` doit être configuré :
```bash
printf '%s' "pypi-VOTRE_JETON" | gh secret set PYPI_API_TOKEN
```

---

## 8. Vérification Post-Publication

Une fois le package publié sur PyPI :

1. **Page PyPI** : [https://pypi.org/project/pyingestkit/](https://pypi.org/project/pyingestkit/)
2. **Test d'installation utilisateur** (dans un environnement vierge) :
   ```bash
   pip install pyingestkit
   ```
3. **Vérification CLI** :
   ```bash
   pyingest --version
   pyingest jobs
   ```

---

## 9. Bonnes Pratiques de Sécurité

- **Jeton restreint (Project-scoped Token)** : Une fois le premier upload réalisé, générer sur PyPI un jeton restreint uniquement au projet `pyingestkit` et remplacer le secret global.
- **PyPI Trusted Publishers (OIDC)** : Pour une sécurité maximale, PyPI supporte l'authentification OIDC sans jeton permanent stocké dans GitHub Secrets.
