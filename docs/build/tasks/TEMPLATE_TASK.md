# TASK-LOT<XX>-<YY> : <Intitulé Précis et Actionnable de la Tâche>

<!-- 
NOMENCLATURE DU FICHIER :
docs/build/tasks/TASK-LOT<NUMERO_LOT>-<NUMERO_TACHE>_<intitule-court-kebab-case>.md
Exemple : docs/build/tasks/TASK-LOT31-03_cli-doctor-command.md
-->

- **Statut :** TODO <!-- TODO | IN_PROGRESS | DONE | BLOCKED -->
- **Plan Parent :** [`docs/build/plans/YYYY-MM-DD_plan-xxxx.md`](../plans/)
- **Assigné à :** <!-- Antigravity / AWF / Nom -->
- **Date de création :** YYYY-MM-DD
- **Date d'achèvement :** <!-- YYYY-MM-DD (si DONE) -->
- **Branche Git :** `feat/<nom-de-branche>`
- **Commit SHA :** <!-- <sha> (si DONE) -->

---

## 1. Contexte & Objectif Unitaire

<!-- 
Expliquer en 2 ou 3 phrases l'action chirurgicale à mener et pourquoi elle est nécessaire.
Mentionner les règles d'or et les invariants à ne pas violer.
-->

L'objectif de cette tâche est d'implémenter ...

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/...` | Création / Modification | Implémentation du composant |
| `tests/unit/.../test_...py` | Création | Tests unitaires isolés (sans I/O réseau ni disque externe) |

---

## 3. Checklist d'Exécution

<!-- 
Checklist granulaire étape par étape.
-->

- [ ] **1. Écriture du code :**
  - [ ] Écrire l'interface / classe avec typage strict (`from __future__ import annotations`).
  - [ ] Respecter la politique de gestion d'erreurs (pas de silent pass, exceptions typées).
- [ ] **2. Tests unitaires :**
  - [ ] Tester le chemin nominal (happy path).
  - [ ] Tester les cas limites et de rejet (edge cases, invalid input).
  - [ ] Vérifier la couverture de code du module cible.
- [ ] **3. Qualité & Formatage :**
  - [ ] `ruff check .`
  - [ ] `ruff format .`
- [ ] **4. Validation sans régression :**
  - [ ] Exécuter la commande de validation ci-dessous.

---

## 4. Preuves & Commandes de Validation

<!-- 
Commandes exactes à lancer pour certifier la conformité de la tâche.
-->

```bash
# Test unitaire ciblé
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/mon_module/test_mon_module.py -v

# Vérification rapide de non-régression
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
```

---

## 5. Résultat & Preuves d'Exécution (À renseigner une fois DONE)

<!-- 
Section à compléter lors du passage au statut DONE.
-->

- **Commit de scellement :** `abcdef12`
- **Résultats des tests :**
  ```text
  X passed in Y.YYs
  ```
- **Remarques éventuelles / Suivi :** ...
