# Gouvernance des Revues de Lot, Clôture Formelle & Discipline Git : `docs/build/reviews/`

Ce répertoire héberge les **revues formelles de qualification de lot**, les **audits de conformité architecturale** et les **décisions officielles de clôture/release** de [`PyIngestKit`](../../../README.md).

---

## 1. Rôle dans le Continuum SDLC

Dans le continuum d'ingénierie de `PyIngestKit`, la revue de lot constitue l'**étape ultime de qualification et de validation** avant fusion et mise en production :

```text
1. Backlog (docs/build/backlog/)       ──> Quoi faire ? (Besoins bruts & dettes)
2. Plans (docs/build/plans/)           ──> Comment cadencer ? (Plans directeurs par LOT)
3. Tâches (docs/build/tasks/)          ──> Actions atomiques de session (WBS)
4. Feedback (docs/build/feedback/)     ──> REX post-tâche & boucle de rétroaction
5. Rapports (docs/build/reports/tests/)──> Preuves objectives de tests
6. Revues (docs/build/reviews/)        ──> Audit de conformité & Clôture formelle
```

La revue de lot :
- Consolide les résultats de toutes les tâches atomiques d'un **Plan Directeur**.
- Vérifie la conformité avec les invariants d'architecture hexagonale et les 11 symboles de la racine.
- Porte la signature officielle (`APPROUVÉ POUR MERGE & RELEASE`) autorisant le merge vers la branche principale `main` et la publication PyPI.

---

## 2. La Règle d'Or : « Clôturer avant de Poursuivre » (*Small Batches & Blast Radius*)

> [!IMPORTANT]
> **Principe Cardinal de Delivery :**
> **Toujours clôturer formellement le lot en cours avant d'entamer le lot suivant du backlog.**
> Il est strictement interdit d'empiler des chantiers techniques hétérogènes sur la même branche de travail.

### Pourquoi cette discipline est impérative :

1. **Maîtrise du rayon d'impact (*Blast Radius*) & *Small Batches* :**
   - Chaque lot (ex: LOT-31 CLI `pik`, LOT-32 Hygiène Racine, LOT-34 CI/CD OIDC) a une responsabilité technique précise.
   - Les regrouper sur une même branche crée des « méga-PR » volumineuses, difficiles à relire, risquées en cas de régression et impossibles à *revert* de manière chirurgicale.

2. **Garantie d'intégrité & *Definition of Done* (DoD) :**
   - Un lot est achevé lorsque **100% des critères de qualification sont validés**.
   - Figer et fusionner le jalon certifie que la branche `main` dispose d'un palier stable et audité.

3. **Base propre pour les développements ultérieurs :**
   - Les lots suivants peuvent s'appuyer en toute confiance sur les livrables déjà fusionnés dans `main` (ex: la commande `pik doctor` pour la CI/CD).

---

## 3. Checklist de la *Definition of Done* (DoD) d'un Lot

Pour qu'un lot soit éligible à la clôture formelle, **TOUS** les critères suivants doivent être validés :

- [ ] **Tâches complétées :** Toutes les tâches associées dans [`docs/build/tasks/`](../tasks/) sont passées à `DONE`.
- [ ] **Feedbacks rédigés :** Une fiche REX existe dans [`docs/build/feedback/`](../feedback/) pour chaque tâche exécutée.
- [ ] **Batterie de tests 100% verte :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make architecture-v2  # 79/79 passés
  PATH="/opt/miniconda3/bin:$PATH" make contract-v2      # 76/76 passés
  PATH="/opt/miniconda3/bin:$PATH" make test-v2          # 367 passés
  ```
- [ ] **Zéro dette de typage / linting :**
  ```bash
  PATH="/opt/miniconda3/bin:$PATH" make quality          # Ruff et Mypy stricts : 0 erreur
  ```
- [ ] **Registre des tâches à jour :** La matrice [`docs/build/tasks/TODOS.md`](../tasks/TODOS.md) affiche le statut `[x] TERMINÉ` et les KPIs à jour.
- [ ] **Fiche de revue signée :** Le document de revue est rédigé dans ce dossier et signé `APPROUVÉ POUR MERGE & RELEASE`.

---

## 4. Protocole Git de Clôture & Enchaînement

Le passage d'un lot achevé au lot suivant suit rigoureusement ces 5 étapes :

```text
[Branche feat/lot-A] ──(1. Push)──> [GitHub PR] ──(2. Review & Merge)──> [main consolidé]
                                                                                │
                                           (4. git checkout -b feat/lot-B) <────┴──(3. git pull origin main)
```

1. **Pousser la branche de travail :**
   ```bash
   git push origin feat/<nom-du-lot-acheve>
   ```
2. **Ouvrir et fusionner la Pull Request :**
   - Relecture ciblée sur le périmètre exact du lot.
   - Squash & Merge ou Merge Commit selon les conventions de l'équipe.
3. **Resynchroniser le dépôt local :**
   ```bash
   git checkout main
   git pull origin main
   ```
4. **Créer la nouvelle branche dédiée pour le lot suivant :**
   ```bash
   git checkout -b feat/<nom-du-nouveau-lot>
   ```
5. **Démarrer les fiches du nouveau lot** dans [`docs/build/tasks/`](../tasks/).

---

## 5. Convention de Nommage des Fiches de Revue

Chaque document de revue est nommé selon la règle :

```text
YYYY-MM-DD_<nom-du-lot>_review.md
```

### Exemples :
- `2026-10-24_lot31_cli-pik-standardization-review.md`
- `2026-10-25_lot32_root-hygiene-and-infra-review.md`
- `2026-10-26_lot34_pypi-oidc-release-automation-review.md`

Pour initialiser une nouvelle revue, copier le gabarit officiel : [`TEMPLATE_LOT_REVIEW.md`](./TEMPLATE_LOT_REVIEW.md).
