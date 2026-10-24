# TASK-LOT31-02 : Sécurité Filesystem & Masquage des Credentials CLI

- **Statut :** ✅ **DONE**
- **Plan Parent :** [`docs/build/plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md`](../plans/2026-10-24_plan-cli-architecture-and-pik-standardization.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-24
- **Date de complétion :** 2026-10-24
- **Branche Git :** `feat/agentic-governance-and-instructions`

---

## 1. Contexte & Objectif Unitaire

Dans le cadre du durcissement de la CLI `pik` et de son alignement sur les standards de `ptk` et `pwk`, doter le sous-système CLI d'un module de sécurité dédié (`security.py`) :
1. **Confinement filesystem strict (Anti Path-Traversal)** : Rejeter formellement tout chemin contenant des null-bytes ou tentant d'échapper au workspace racine via des séquences `../`.
2. **Masquage systématique des credentials (Redaction)** : Masquer les mots de passe dans les URIs (`postgresql://user:password@host`), ainsi que les clés d'API, tokens et secrets dans les flux textuels et messages d'erreur.
3. **Codes de sortie conformes** : Renvoyer l'exception `SecurityError` associée au code de sortie standard `ExitCode.SECURITY_ERROR` (4).

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/cli/security.py` | Création | Helpers `sanitize_input_path`, `assert_path_within_workspace`, `redact_sensitive_text`, `redact_mapping` |
| `tests/unit/cli/test_security.py` | Création | Tests unitaires de validation de confinement et masquage regex |

---

## 3. Checklist d'Exécution

- [x] **1. Écriture de `src/pyingestkit/cli/security.py` :**
  - [x] Définir la constante `REDACTED = "[REDACTED]"`.
  - [x] Définir l'exception `SecurityError` rattachée à `ExitCode.SECURITY_ERROR` (code 4).
  - [x] Implémenter `sanitize_input_path(raw_path: str | Path) -> Path` avec rejet des null-bytes (`\0`).
  - [x] Implémenter `assert_path_within_workspace(path: str | Path, workspace_root: str | Path | None = None) -> Path`.
  - [x] Implémenter `redact_sensitive_text(text: str) -> str` masquant URIs et paires clé/valeur sensibles.
  - [x] Implémenter `redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]` pour les métadonnées et configs.
- [x] **2. Écriture des tests sous `tests/unit/cli/test_security.py` :**
  - [x] Tester les chemins valides dans le workspace.
  - [x] Tester la détection et le rejet de `../../outside.txt` ou chemins hors workspace.
  - [x] Tester le rejet de chemins contenant des null-bytes.
  - [x] Tester le masquage des URIs de base de données (PostgreSQL, S3).
  - [x] Tester le masquage des affectations `api_key=...`, `token: ...`, `password=...`.
  - [x] Tester le masquage des en-têtes `Authorization: Bearer ...`.
- [x] **3. Qualité & Intégration :**
  - [x] `ruff check` et `ruff format` : 384 files already formatted.
  - [x] `make architecture-v2` : 79/79 passed.
  - [x] `make contract-v2` : 76/76 passed.
  - [x] `make test-v2` : 367 passed, 25 skipped.
  - [x] `make quality` : mypy 0 issues in 104 files.

---

## 4. Preuves & Commandes de Validation

```bash
# Tests unitaires de sécurité CLI
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/test_security.py -v
# ============================== 9 passed in 0.08s ===============================

# Ensemble de la suite CLI
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/cli/ -v
# ============================== 18 passed in 0.38s ==============================

# Vérification architecture et qualité
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
# 79 passed in 1.39s

PATH="/opt/miniconda3/bin:$PATH" make quality
# All checks passed! 384 files already formatted. Success: no issues found in 104 source files.
```
