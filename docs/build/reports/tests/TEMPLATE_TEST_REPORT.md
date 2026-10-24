# Rapport de Qualification & Preuves de Tests : <Jalon ou LOT>

<!-- 
NOMENCLATURE DU FICHIER :
docs/build/reports/tests/YYYY-MM-DD_<version-ou-lot>_qualification-test-report.md
Exemple : docs/build/reports/tests/2026-10-25_lot31_cli-qualification-report.md
-->

- **Jalon / Version :** <!-- v2.1.0 / LOT-31 -->
- **Date d'exécution :** YYYY-MM-DD
- **Opérateur / Agent :** <!-- Antigravity / AWF / CI Runner -->
- **Environnement d'exécution :** Python 3.13 (Miniconda / Linux / macOS)
- **Commit SHA testé :** `abcdef12`
- **Résultat Global :** ✅ **QUALIFIÉ SANS RÉGRESSION** <!-- QUALIFIÉ | ÉCHEC | RÉSERVES -->

---

## 1. Synthèse des Résultats par Suite de Tests

| Suite de Tests | Commande Exécutée | Passés | Échoués | Ignorés | Durée | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Architecture V2** | `make architecture-v2` | 79 | 0 | 0 | 0.44s | ✅ PASS |
| **Contrats V1/V2** | `make contract-v2` | 76 | 0 | 0 | 0.38s | ✅ PASS |
| **Tests Unitaires & Intégration** | `make test-v2` | 367 | 0 | 25 | 3.43s | ✅ PASS |
| **Contrôle Qualité & Lint** | `ruff check .` | 0 err | 0 | 0 | 0.12s | ✅ PASS |
| **Typage Statique** | `mypy src/` | Clean | 0 | 0 | 1.05s | ✅ PASS |

---

## 2. Validation des Invariants Non-Négociables

- [x] **API Racine V2 gelée :** Exactement 11 symboles publics exportés par `src/pyingestkit/__init__.py`.
- [x] **Fixtures de contrat immuables :** Aucun diff constaté sur `tests/contract/fixtures/`.
- [x] **Zéro fuite d'abstractions V1 :** Aucune réintroduction des classes `Job`, `Pipeline`, `Runner` à la racine V2.
- [x] **Publication Ledger :** Intégrité transactionnelle vérifiée (CAS validé sous SQLite et PostgreSQL).

---

## 3. Détail des Logs d'Exécution

### A. Trace `make architecture-v2`
```text
PYTHONPATH=src pytest -q tests/architecture
............................................................................... [100%]
79 passed in 0.44s
```

### B. Trace `make contract-v2`
```text
PYTHONPATH=src pytest -q tests/contract/public_api
............................................................................    [100%]
76 passed in 0.38s
```

---

## 4. Métriques de Couverture de Code (Optionnel)

- **Total Statements :** 4 820
- **Couverture Globale :** 94.2 %
- **Couverture Core Domain :** 100 %

---

## 5. Conclusion & Décision de Clôture

Le présent procès-verbal atteste que les livrables du lot satisfont 100 % des exigences de qualité, de stabilité et de non-régression.
Le lot est déclaré **apte au merge et à la release**.
