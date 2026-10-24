# Boucle de Rétroaction & Retours d'Expérience (REX) : `docs/build/feedback/`

Ce répertoire héberge les **fiches de feedback post-implémentation** issues des sessions de développement et du pair-programming avec les agents IA ([`PyIngestKit`](../../README.md)).

---

## 1. Rôle dans l'Agentic SDLC (La *Feedback Loop*)

La boucle de rétroaction (*feedback loop*) est le mécanisme d'apprentissage continu qui garantit que :
1. **Les frictions rencontrées lors d'une tâche** ne se reproduisent pas lors des tâches suivantes.
2. **Les bonnes pratiques émergentes** sont capitalisées et réinjectées dans les instructions canoniques ([`AGENTS.md`](../../AGENTS.md) / [`CLAUDE.md`](../../CLAUDE.md)).
3. **Les dettes ou besoins découverts** pendant le développement sont immédiatement réinjectés dans le backlog ([`docs/build/backlog/`](../backlog/)).

```text
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| LA BOUCLE DE RÉTROACTION DANS LE CYCLE SDLC                                                       |
|                                                                                                   |
|           ┌────────────────────────────────────────────────────────┐                              |
|           │              1. TÂCHE WBS (docs/build/tasks/)          │                              |
|           │              Implémentation chirurgicale ciblée        │                              |
|           └───────────────────────────┬────────────────────────────┘                              |
|                                       │                                                           |
|                                       ▼                                                           |
|           ┌────────────────────────────────────────────────────────┐                              |
|           │          2. FEEDBACK POST-IMPLÉMENTATION               │                              |
|           │          (docs/build/feedback/)                        │                              |
|           │          • Ce qui a bien fonctionné                    │                              |
|           │          • Frictions, arbitrages (ex: infra/ vs deploy)│                              |
|           │          • Leçons apprises & axes d'amélioration       │                              |
|           └──────────────┬──────────────────────────┬──────────────┘                              |
|                          │                          │                                             |
|        (Dette découverte)│                          │(Ajustement règles)                          |
|                          ▼                          ▼                                             |
|        ┌─────────────────────────────┐   ┌─────────────────────────────┐                          |
|        │ BACKLOG (docs/build/backlog)│   │ AGENTS.md / CLAUDE.md       │                          |
|        │ Nouvel item qualifié        │   │ Verrouillage invariants     │                          |
|        └─────────────────────────────┘   └─────────────────────────────┘                          |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Nomenclature des Fiches de Feedback

Chaque fichier de feedback respecte la convention :

```text
FEEDBACK-LOT<NUMERO_LOT>-<INDEX_TACHE>_<intitule-court-kebab-case>.md
```

### Exemples :
- `FEEDBACK-LOT32-01_root-hygiene-reorganization.md`
- `FEEDBACK-LOT31-01_cli-bootstrap-and-exit-codes.md`

---

## 3. Template de Référence

Pour documenter un retour de session, dupliquez le template officiel :
```bash
cp docs/build/feedback/TEMPLATE_FEEDBACK.md docs/build/feedback/FEEDBACK-LOTXX-YY_mon-sujet.md
```

---

## 4. Registre des Feedbacks

| Réf. Feedback | Tâche Évaluée | Auteur | Date | Impact Majeur / Apprentissage |
| :--- | :--- | :--- | :--- | :--- |
| [`FEEDBACK-LOT32-01`](./FEEDBACK-LOT32-01_root-hygiene-reorganization.md) | `TASK-LOT32-01` (Nettoyage racine) | Antigravity / AWF | 2026-10-24 | Choix du nom canonique `infra/` au lieu de `deployment/` ; protection `.gitignore`. |
