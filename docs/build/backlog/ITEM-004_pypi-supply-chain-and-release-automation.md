# ITEM-004 : Automatisation de la Supply Chain & Publication PyPI via Trusted Publishing

- **Statut :** PLANNED
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** CRITIQUE
- **Composant Cible :** CI/CD & Sécurité (`.github/workflows/`)
- **Plan Associé :** [`docs/build/plans/2026-10-24_plan-release-automation-and-supply-chain.md`](../plans/2026-10-24_plan-release-automation-and-supply-chain.md)
- **LOT Cible :** LOT-34

---

## 1. Contexte & Problématique Constatée

La publication des distributions sur PyPI reposait jusqu'ici sur des interventions manuelles (`twine upload` avec token API local), ce qui explique pourquoi la version 2.0.0 n'avait jamais été publiée sur PyPI.
De plus, la chaîne de distribution ne comportait ni génération de SBOM (Software Bill of Materials) CycloneDX, ni attestations cryptographiques Sigstore de build provenance, contrairement à `pytransformkit` et `pyworkflowkit`.

---

## 2. Expression du Besoin & User Story

- **En tant que :** Mainteneur du repository et utilisateur de PyIngestKit en production.
- **Je souhaite :** Un workflow GitHub Actions de publication entièrement automatisé sur création de tag Git (`v*.*.*`), s'appuyant sur l'authentification OIDC sans secret (*Trusted Publishing*).
- **Afin de :** Garantir des releases immédiates, reproductibles et vérifiables sans dépendre de tokens stockés manuellement.

---

## 3. Bénéfices Attendus

1. **Sécurité :** Zéro token API permanent dans GitHub Secrets (OIDC éphémère).
2. **Conformité Supply Chain :** SBOM CycloneDX v1.5 JSON généré et téléversé sur GitHub Releases.
3. **Traçabilité :** Attestations cryptographiques Sigstore (`gh-action-sigstore-python`).

---

## 4. Invariants

- [x] Déclenchement strict uniquement sur push de tag `v*.*.*`.
- [x] Vérification de l'adéquation entre le tag Git et `src/pyingestkit/_version.py`.
- [x] Vérification d'intégrité `sha256sum -c SHA256SUMS`.

---

## 5. Livrables Associés

- Plan d'implémentation : [`docs/build/plans/2026-10-24_plan-release-automation-and-supply-chain.md`](../plans/2026-10-24_plan-release-automation-and-supply-chain.md)
- Fichier workflow : `.github/workflows/publish-pypi.yml`
