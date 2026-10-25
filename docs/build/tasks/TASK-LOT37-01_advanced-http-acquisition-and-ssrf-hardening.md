# TASK-LOT37-01 : Acquisition HTTP Avancée, Rafraîchissement OAuth & Durcissement SSRF

- **Statut :** ✅ DONE
- **Plan Parent :** [`docs/build/plans/2026-10-25_plan-advanced-http-acquisition-and-ssrf-hardening.md`](../plans/2026-10-25_plan-advanced-http-acquisition-and-ssrf-hardening.md)
- **Item Backlog :** [`docs/build/backlog/ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md`](../backlog/ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md)
- **Assigné à :** Antigravity / AWF
- **Date de création :** 2026-10-25
- **Date d'achèvement :** 2026-10-25
- **Branche Git :** `feat/http-ssrf-hardening-and-oauth`
- **Commit SHA :** [`8e77f8c`](https://github.com/tawounfouet/pyingestkit/commit/8e77f8c1be918da8912b8291dbafbe85c674292a) (PR [#73](https://github.com/tawounfouet/pyingestkit/pull/73))

---

## 1. Contexte & Objectif Unitaire

L'objectif de cette tâche est d'implémenter les capacités d'acquisition HTTP durcie de PyIngestKit V2 (LOT-37) :
1. Construire le bouclier anti-SSRF stdlib (`_ssrf.py`) avec validation stricte des adresses IP (IPv4 et IPv6) contre les plages loopback, RFC 1918, link-local, cloud metadata (`169.254.169.254`), et exemptions contrôlées (`allow_private_networks`, `allowed_ip_ranges`).
2. Étendre les contrats `HttpRequestV2` (avec `method`, `body`, `pinned_ip`) et `HttpAccessPolicy` dans `transport.py` et `source.py`.
3. Concevoir le module de cycle de vie des jetons OAuth 2.0 (`oauth.py`) avec gestionnaires thread-safe pour les flux Client Credentials et Refresh Token, détection d'expiration 401 et renouvellement transparent, sans fuite de secrets.
4. Intégrer un transport HTTPX personnalisé avec `SsrfSafeNetworkBackend` garantissant l'immunité au DNS Rebinding via épinglage de l'IP validée à l'ouverture de la socket TCP tout en préservant le SNI et la vérification des certificats TLS/SSL.
5. Intégrer le support complet dans `HttpSourceConnector` avec extraction non-invasive des options HTTP depuis `source.metadata`, retry exponentiel avec Full Jitter, et qualification de l'incertitude réseau (`OutcomeUncertainty.REQUIRES_RECONCILIATION` sur timeout `POST`/`PUT`).
6. Valider l'implémentation par une suite de tests unitaires exhaustifs, un guide d'utilisation et les portes qualité strictes.

---

## 2. Périmètre des Fichiers

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `src/pyingestkit/adapters/http/_ssrf.py` | **Création** | Validateur d'adresses IP stdlib, détection des plages réservées, exceptions SSRF |
| `src/pyingestkit/adapters/http/oauth.py` | **Création** | Modèles `OAuthToken`, interfaces providers, implémentations client_credentials & refresh_token, `OAuthTokenManager` thread-safe |
| `src/pyingestkit/adapters/http/transport.py` | **Modification** | Ajout de `method`, `body`, `pinned_ip` dans `HttpRequestV2` |
| `src/pyingestkit/adapters/http/_httpx.py` | **Modification** | Intégration du `SsrfSafeNetworkBackend` pour épinglage socket, support streaming pour `POST`/`PUT` |
| `src/pyingestkit/adapters/http/source.py` | **Modification** | Évolution de `HttpAccessPolicy` (private networks, jitter), extraction non-invasive des options HTTP, interception 401, qualification de l'incertitude |
| `tests/unit/v2/test_http_ssrf.py` | **Création** | Tests unitaires exhaustifs du bouclier anti-SSRF (loopback, private, metadata, IPv6, exemptions) |
| `tests/unit/v2/test_http_oauth.py` | **Création** | Tests unitaires du gestionnaire OAuth 2.0 (cache, expiration, refresh transparent, redaction des secrets) |
| `tests/unit/v2/test_http_transport_v2.py` | **Création** | Tests unitaires des méthodes HTTP, payloads, timeouts et qualification d'incertitude |
| `docs/guides/http-acquisition-and-ssrf-hardening.md` | **Création** | Guide utilisateur complet pour l'acquisition HTTP sécurisée |
| `mkdocs.yml` | **Modification** | Déclaration du nouveau guide dans la navigation |
| `docs/build/tasks/TODOS.md` | **Modification** | Enregistrement de la tâche et suivi d'avancement |

---

## 3. Checklist d'Exécution

- [x] **Étape 1 :** Développer `src/pyingestkit/adapters/http/_ssrf.py` (Validation d'adresses IP, détection des plages privées/metadata/loopback, résolution sécurisée).
- [x] **Étape 2 :** Étendre `HttpRequestV2` et `HttpAccessPolicy` dans `src/pyingestkit/adapters/http/transport.py` et `source.py`.
- [x] **Étape 3 :** Développer `src/pyingestkit/adapters/http/oauth.py` (Modèles `OAuthToken`, `ClientCredentialsOAuthProvider`, `RefreshTokenOAuthProvider`, `OAuthTokenManager` thread-safe avec redaction intégrale).
- [x] **Étape 4 :** Adapter `src/pyingestkit/adapters/http/_httpx.py` avec `SsrfSafeNetworkBackend` et streaming de requêtes avec corps (`POST`/`PUT`).
- [x] **Étape 5 :** Intégrer la logique globale dans `src/pyingestkit/adapters/http/source.py` (anti-SSRF, OAuth 401 auto-refresh, retry Full Jitter, `OutcomeUncertainty.REQUIRES_RECONCILIATION`).
- [x] **Étape 6 :** Rédiger les tests unitaires (`test_http_ssrf.py`, `test_http_oauth.py`, `test_http_transport_v2.py`).
- [x] **Étape 7 :** Rédiger le guide d'utilisation `docs/guides/http-acquisition-and-ssrf-hardening.md` et mettre à jour `mkdocs.yml`.
- [x] **Étape 8 :** Valider l'ensemble de la suite (`make quality`, `make architecture-v2`, `make test-v2`, `mkdocs build --strict`).
- [x] **Étape 9 :** Rédiger la fiche REX `FEEDBACK-LOT37-01` et la revue formelle de clôture de jalon.

---

## 4. Preuves & Commandes de Validation

```bash
PATH="/opt/miniconda3/bin:$PATH" make quality
PATH="/opt/miniconda3/bin:$PATH" make architecture-v2
PATH="/opt/miniconda3/bin:$PATH" make test-v2
PATH="/opt/miniconda3/bin:$PATH" pytest tests/unit/v2/test_http_ssrf.py tests/unit/v2/test_http_oauth.py tests/unit/v2/test_http_transport_v2.py -v
PATH="/opt/miniconda3/bin:$PATH" mkdocs build --strict
```

---

## 5. Résultat & Clôture de Tâche

- **Statut final :** ✅ DONE
- **Commit / PR :** Branche `feat/http-ssrf-hardening-and-oauth`
- **Fiche REX associée :** [`docs/build/feedback/FEEDBACK-LOT37-01_advanced-http-acquisition-and-ssrf-hardening.md`](../feedback/FEEDBACK-LOT37-01_advanced-http-acquisition-and-ssrf-hardening.md)
- **Revue de lot associée :** [`docs/build/reviews/2026-10-25_lot37_advanced-http-acquisition-and-ssrf-hardening-review.md`](../reviews/2026-10-25_lot37_advanced-http-acquisition-and-ssrf-hardening-review.md)
