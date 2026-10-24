# Procès-Verbaux & Rapports de Qualification de Tests : `docs/build/reports/tests/`

Ce répertoire héberge les **preuves d'exécution**, rapports de qualification de releases et matrices de couverture de tests générées lors des jalons de livraison de [`PyIngestKit`](../../../README.md).

---

## 1. Rôle dans l'Assurance Qualité

Ce dossier reçoit les livrables d'exécution de tests (les fichiers Markdown, HTML ou JSON attestant de la non-régression) :
- **Procès-verbaux de passage de jalon** (ex: PV d'exécution des 367 tests de la V2.1.0).
- **Rapports de couverture** (Coverage.py, lcov).
- **Traces de qualification d'architecture** (`make architecture-v2` - 79 tests).
- **Traces de conformité contractuelle** (`make contract-v2` - 76 tests).

> **Rappel d'Architecture :** Le code de test automatisé vit exclusivement dans [`tests/`](../../../tests/) à la racine du package. Ce répertoire ne contient que la documentation et les preuves de résultats.

---

## 2. Convention de Nommage des Rapports

```text
YYYY-MM-DD_<version-ou-lot>_test-qualification-report.md
```

### Exemple :
- `2026-10-24_v2.1.0_qualification-test-report.md`
