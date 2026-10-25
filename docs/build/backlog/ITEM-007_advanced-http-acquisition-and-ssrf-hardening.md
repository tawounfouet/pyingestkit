# ITEM-007 : Acquisition HTTP Avancée, Rafraîchissement OAuth & Durcissement SSRF

- **Statut :** DONE
- **Auteur :** Antigravity / AWF
- **Date d'émission :** 2026-10-24
- **Priorité :** MOYENNE
- **Composant Cible :** HTTP Source Adapter (`src/pyingestkit/adapters/sources/http/`)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../../roadmap/post-2.0-scope-review.md) (Section 3.4)
- **LOT Cible :** LOT-37 (v2.3.0)

---

## 1. Contexte & Problématique Constatée

Le connecteur source HTTP actuel gère principalement des requêtes de type `GET` avec authentification par token statique (Bearer ou API Key).
Dans les architectures d'ingestion d'API SaaS modernes (Salesforce, Stripe, HubSpot), plusieurs besoins cruciaux émergent :
1. Nécessité de déclencher des requêtes `POST` ou `PUT` avec payload JSON pour les API de pagination basées sur curseur.
2. Gestion du cycle de vie des tokens OAuth 2.0 (rafraîchissement automatique de token expiré à la frontière du connecteur).
3. Risques de sécurité de type SSRF (*Server-Side Request Forgery*) nécessitant une validation stricte des adresses IP résolues (interdiction des plages privées RFC 1918 et link-local `169.254.169.254`).

---

## 2. Expression du Besoin & User Story

- **En tant que :** Développeur intégrant des API REST tierces sécurisées.
- **Je souhaite :** Configurer un provider HTTP avec rotation automatique de jeton OAuth et protection active contre les dérives SSRF.
- **Afin de :** Collecter des données sans interruption de service tout en protégeant les réseaux internes d'entreprise.

---

## 3. Bénéfices Attendus

1. **Sécurité maximale :** Protection anti-SSRF de niveau DNS/IP au niveau du transport HTTP.
2. **Autonomie :** Reconnexion et renouvellement transparents des jetons OAuth sans redémarrage de pipeline.
3. **Traçabilité :** Enregistrement des en-têtes HTTP de corrélation (`X-Request-ID`) dans les preuves RAW sans fuite de secrets.

---

## 4. Invariants

- [ ] Tout secret ou token OAuth doit être strictement exclu des artefacts d'audit et des logs.
- [ ] Le transport HTTP reste optionnel (sous l'extra `[http]`) et n'alourdit pas l'installation de base.
- [ ] Idempotence préservée en cas d'incertitude réseau (`OutcomeUncertainty`).
