# Analyse Technique & Architecture : Acquisition HTTP Avancée, Rafraîchissement OAuth & Durcissement SSRF — LOT-37

- **Date :** 2026-10-25
- **Auteur :** Antigravity / Pair Programming
- **Item Backlog :** [`docs/build/backlog/ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md`](../build/backlog/ITEM-007_advanced-http-acquisition-and-ssrf-hardening.md)
- **Document Source :** [`docs/roadmap/post-2.0-scope-review.md`](../roadmap/post-2.0-scope-review.md) (Section 3.4)
- **LOT Cible :** LOT-37 (v2.3.0)
- **Références amont :**
  - Note de cadrage préalable : [`docs/analyses/cadrage/2026-10-25_cadrage-lot37-advanced-http-acquisition-and-ssrf-hardening.md`](./cadrage/2026-10-25_cadrage-lot37-advanced-http-acquisition-and-ssrf-hardening.md)
  - [`docs/architecture/http-acquisition-alpha1.md`](../architecture/http-acquisition-alpha1.md)
  - [`docs/adr/ADR-022-httpx-default-http-transport.md`](../adr/ADR-022-httpx-default-http-transport.md)
  - [`docs/adr/ADR-023-retry-policy-idempotency.md`](../adr/ADR-023-retry-policy-idempotency.md)
  - [`docs/adr/ADR-009-secret-handling.md`](../adr/ADR-009-secret-handling.md)

---

## 1. Contexte & Problématique Métier

Dans PyIngestKit V2 (introduit au LOT-14 et consolidé au LOT-36), le connecteur source HTTP (`HttpSourceConnector`) encapsule le protocole d'acquisition de données distantes via le port d'abstraction `HttpClientV2` et son adaptateur concret `HttpxHttpClientV2`.

Dans les contextes d'ingestion de données de production (connecteurs d'APIs SaaS telles que Stripe, Salesforce, HubSpot, Google Cloud APIs, Shopify ou Elasticsearch), les architectures modernes imposent des exigences de sécurité et de résilience bien supérieures à un simple téléchargement de fichiers :

1. **Interrogation via requêtes à corps (`POST`, `PUT`) :**
   - De nombreuses APIs de référence ne permettent pas d'exprimer des requêtes complexes uniquement dans l'URL. Les filtres avancés, les payloads GraphQL, ou les recherches paginées par curseur (ex: `/v1/search` chez Stripe ou `/services/data/vXX.X/jobs/query` chez Salesforce) exigent une méthode `POST` avec un corps structuré JSON ou x-www-form-urlencoded.
   - Actuellement, `HttpRequestV2` et `HttpxHttpClientV2` sont limités de manière rigide au verbe `GET` sans payload.

2. **Cycle de vie dynamique des jetons OAuth 2.0 :**
   - L'authentification par jeton statique (`HttpCredentialResolverV2`) est inopérante pour les flux batch de longue durée : un jeton d'accès expire typiquement après 60 minutes.
   - Lorsque le serveur distant répond par un code `401 Unauthorized`, le pipeline s'interrompt brutalement. L'adaptateur doit être capable d'intercepter cette expiration, de renouveler le jeton de manière autonome (via `client_credentials` ou `refresh_token`), et de rejouer la requête de manière transparente.

3. **Menaces critiques de sécurité : SSRF (*Server-Side Request Forgery*) & DNS Rebinding :**
   - Le connecteur actuel se contente d'un filtrage lexical sur le nom de domaine (`host in self.allowed_hosts`).
   - Cette approche est vulnérable à :
     - La résolution d'un domaine légitime vers une adresse IP interne (réseaux privés RFC 1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, loopback `127.0.0.1`, ou l'adresse sensible de métadonnées cloud `169.254.169.254`).
     - L'attaque par **DNS Rebinding** : le nom d'hôte résout vers une IP publique lors du contrôle pré-vol, puis vers `169.254.169.254` au moment où la socket TCP est établie par HTTPX.
     - Les redirections HTTP ouvertes (`302 Found` vers une cible interne).

4. **Résilience réseau & Qualification de l'Incertitude (`OutcomeUncertainty`) :**
   - Un mécanisme de retry sans gigue (*jitter*) provoque des congestions synchronisées lors des pannes de passerelles SaaS.
   - De surcroît, une coupure réseau survenant pendant une requête `POST` crée un risque majeur de duplication d'effets de bord si l'échec n'est pas qualifié d'`OutcomeUncertainty.UNCERTAIN`.

---

## 2. Benchmark & État de l'Art

| Mécanisme de Protection / Transport | Approche Naïve (Actuelle) | Approche Interception Proxy | Approche Épinglage Socket & Transport Durci (Cible LOT-37) |
| :--- | :--- | :--- | :--- |
| **Validation Hôte / Domaine** | Vérification textuelle `allowed_hosts` | Filtrage au niveau du proxy externe | **Validation textuelle + Port strict** |
| **Résolution IP & Anti-SSRF** | **Aucune** (Vulnérable RFC 1918 & Cloud Metadata) | Déléguée au proxy d'entreprise | **Inspection systématique via `ipaddress` (Zero-Trust)** |
| **Résistance au DNS Rebinding** | **Nulle** (Time-of-check to time-of-use flaw) | Partielle | **Absolue (Épinglage IP direct au niveau `connect_tcp`)** |
| **Support Méthodes & Payloads** | `GET` uniquement, 0 corps | Dépend du client | **`GET`, `POST`, `PUT`, `HEAD` avec streaming borné** |
| **Gestion OAuth 2.0** | En-têtes statiques figés | Scripts manuels hors-bande | **Provider natif avec cache, TTL, clock skew & auto-refresh 401** |
| **Idempotence & Incertitude** | Incertitude non qualifiée (`KNOWN` forcé) | Non modélisé | **`UNCERTAIN` sur timeout `POST`, `KNOWN` sur `GET`** |

---

## 3. Analyse des Options Architecturales

### Option 1 : Déporter la sécurité SSRF sur un reverse-proxy d'infrastructure (ex: Envoy / Squid)
- *Principe :* Forcer toutes les requêtes sortantes de PyIngestKit à traverser un proxy HTTP filtrant.
- *Rejet :* Impose une dépendance d'infrastructure lourde incompatible avec l'utilisation de PyIngestKit en bibliothèque embarquée, en CLI (`pik`), ou en conteneur éphémère serverless (Cloud Run, AWS Lambda).

### Option 2 : Réécriture d'URL avec adresse IP résolue
- *Principe :* Remplacer le nom d'hôte dans l'URL par l'adresse IP validée (`https://93.184.216.34/path`) et positionner l'en-tête `Host: example.com`.
- *Rejet :* Casse la validation des certificats TLS/SSL et le SNI (*Server Name Indication*), à moins de désactiver la vérification SSL (inacceptable en production) ou de manipuler des contextes SSL complexes pour chaque requête.

### Option 3 (Retenue) : Network Backend Durci HTTPX + Validation IP Déterministe + Provider OAuth Découplé
- *Principe :* 
  1. Un module de sécurité pur stdlib (`_ssrf.py`) qui résout et valide toutes les adresses IP contre une matrice stricte (rejet automatique de loopback, RFC 1918, link-local, cloud metadata, multicast, broadcast).
  2. Un `NetworkBackend` personnalisé pour HTTPX / httpcore (`connect_tcp`) qui prend en charge l'épinglage de l'IP validée directement à l'ouverture de socket, garantissant l'immunité au DNS rebinding tout en conservant 100% de la validation TLS standard.
  3. Un gestionnaire de jetons OAuth 2.0 thread-safe avec masquage cryptographique automatique de tous les secrets.
  4. Transmission non-invasive du verbe et du payload via les métadonnées de requête pour préserver la pureté du domaine universel.

---

## 4. Architecture Détaillée & Diagrammes

```mermaid
flowchart TD
    subgraph Core["Domaine PyIngestKit (Pur)"]
        Req["AcquisitionRequest"]
        Meta["source.metadata: http_method, http_payload"]
    end

    subgraph Connector["HttpSourceConnector"]
        VPolicy["Validation Politique (Hôte, Schéma, Port)"]
        SsrfCheck["AntiSsrfValidator.validate_and_resolve()"]
        TokenResolve["OAuthTokenManager.get_authorization_header()"]
    end

    subgraph SsrfModule["Module Anti-SSRF (_ssrf.py)"]
        DNS["socket.getaddrinfo()"]
        IPVal{"ipaddress validation"}
        PrivateCheck{"allow_private_networks ?"}
    end

    subgraph TransportLayer["Couche Transport Durcie (_httpx.py)"]
        Backend["SsrfSafeNetworkBackend.connect_tcp()"]
        SocketConn["Socket TCP (IP Épinglée)"]
        TLSHandshake["stream.start_tls(server_hostname=host)"]
        StreamSend["Streaming Borné (max_bytes)"]
    end

    subgraph PostProcessing["Gestion Retries & Réponses"]
        RespJudge{"Status Code"}
        RefreshCase["401 -> Refresh Token & Rejeu Unique"]
        RetryCase["429 / 5xx -> Exponential Backoff + Jitter"]
        ResultSuccess["200 OK -> AcquisitionResult (SHA256, Audit RAW)"]
        ResultFailure["Erreur -> FailureEvidence (OutcomeUncertainty)"]
    end

    Req --> VPolicy
    Meta --> VPolicy
    VPolicy --> SsrfCheck
    SsrfCheck --> DNS
    DNS --> IPVal
    IPVal -->|Loopback / LinkLocal / Metadata| BlockSSRF["Échec acquisition.http.ssrf_blocked"]
    IPVal -->|RFC 1918 Privée| PrivateCheck
    PrivateCheck -->|False (Défaut)| BlockSSRF
    PrivateCheck -->|True (Exemption)| OKIP["IP Approuvée"]
    IPVal -->|Publique| OKIP

    OKIP --> TokenResolve
    TokenResolve --> Backend
    Backend --> SocketConn
    SocketConn --> TLSHandshake
    TLSHandshake --> StreamSend
    StreamSend --> RespJudge

    RespJudge -->|2xx| ResultSuccess
    RespJudge -->|401| RefreshCase
    RefreshCase -->|Token Renouvelé| StreamSend
    RefreshCase -->|Échec| ResultFailure
    RespJudge -->|429/5xx/Timeout| RetryCase
    RetryCase --> StreamSend
    RespJudge -->|Erreur Fatale| ResultFailure
```

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      AcquisitionRequest (V2)                           │
│  - source.locator : "https://api.example.com/v1/search"                │
│  - source.metadata : (("http_method", "POST"), ("http_payload", "..."))│
│  - source.credential : CredentialReference("oauth-saas")               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        HttpSourceConnector                             │
│  1. Validation Schéma (https obligatoire sauf allow_http=True)         │
│  2. Validation Hôte & Port autorisés dans HttpAccessPolicy             │
│  3. Validation Anti-SSRF & Résolution DNS (AntiSsrfValidator)          │
│     ├── Résolution DNS via socket.getaddrinfo                          │
│     ├── Rejet immédiat : Loopback (127.0.0.0/8, ::1)                   │
│     ├── Rejet immédiat : Link-Local & Cloud Metadata (169.254.169.254) │
│     ├── Rejet immédiat : RFC 1918 (sauf allow_private_networks=True)   │
│     └── Élection de l'IP validée pour épinglage socket                 │
│  4. Résolution d'Autorisation (OAuthTokenManager / CredentialResolver) │
│     └── Récupération du Bearer token (cache mémoire ou token_url)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              HttpxHttpClientV2 (avec SsrfSafeNetworkBackend)           │
│  - connect_tcp(host, port) se connecte strictement sur l'IP validée    │
│  - Immunité absolue contre le DNS Rebinding                            │
│  - start_tls(server_hostname=host) préserve la validation SSL/SNI      │
│  - Envoi de la requête (GET, POST, PUT, HEAD) et du payload            │
│  - Consommation bornée du flux réponse (rejet si > max_bytes)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────┐                         ┌──────────────────────┐
│  Statut Succès (2xx)  │                         │   Statuts d'Écart    │
└──────────┬────────────┘                         └──────────┬───────────┘
           │                                                 │
           │                                 ┌───────────────┼───────────────┐
           ▼                                 ▼               ▼               ▼
┌───────────────────────┐             ┌────────────┐  ┌────────────┐  ┌────────────┐
│   AcquisitionResult   │             │ 3xx Redir  │  │  401 Auth  │  │ 429/5xx/TO │
│ - Content + SHA256    │             └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
│ - Preuves d'audit RAW │                   │               │               │
│ - Zéro secret fuité   │       Re-validation SSRF     Auto-Refresh    Full Jitter
└───────────────────────┘       stricte de la cible    Jeton OAuth     OutcomeUncert.
```

---

## 5. Spécification Détaillée des Nouveaux Modules & Contrats

### A. Bouclier Anti-SSRF (`src/pyingestkit/adapters/http/_ssrf.py`)

Ce module, indépendant de toute dépendance tierce, implémente les contrôles de sécurité réseau :

```python
class SsrfSecurityError(HttpTransportErrorV2):
    """Exception levée en cas de tentative de connexion à une adresse IP interdite."""

@dataclass(frozen=True, slots=True)
class AntiSsrfValidator:
    allow_private_networks: bool = False
    allowed_ip_ranges: tuple[str, ...] = ()

    def validate_ip(self, ip_str: str) -> None:
        """Valide qu'une adresse IP n'appartient à aucune plage réservée ou interdite."""
        ...

    def resolve_and_validate(self, host: str, port: int) -> tuple[str, ...]:
        """Résout le nom d'hôte via DNS et valide toutes les adresses IP retournées."""
        ...
```

**Plages IP bloquées inconditionnellement :**
- Loopback : `127.0.0.0/8`, `::1/128`
- Link-Local & Cloud Metadata : `169.254.0.0/16`, `fe80::/10`, `169.254.169.254/32`
- Multicast & Broadcast : `224.0.0.0/4`, `ff00::/8`, `255.255.255.255/32`
- Reserved / Benchmark / Carrier-grade NAT : `0.0.0.0/8`, `100.64.0.0/10`, `192.0.0.0/24`, `198.18.0.0/15`
- IPv4-mapped IPv6 : `::ffff:0:0/96` (déplié et inspecté selon les règles IPv4)
- RFC 1918 privées (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`) : bloquées par défaut, autorisées uniquement si `allow_private_networks=True` ou explicitement listées dans `allowed_ip_ranges`.

### B. Évolution de `HttpAccessPolicy` & Contrats de Transport

Dans `src/pyingestkit/adapters/http/source.py` :

```python
@dataclass(frozen=True, slots=True)
class HttpAccessPolicy:
    allowed_hosts: tuple[str, ...]
    max_bytes: int = 128 * 1024 * 1024
    timeout_seconds: float = 30.0
    max_redirects: int = 5
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    max_retry_after_seconds: float = 60.0
    retry_statuses: tuple[int, ...] = _DEFAULT_RETRY_STATUSES
    allow_http: bool = False
    allowed_ports: tuple[int, ...] = ()
    allow_private_networks: bool = False       # Nouveau (LOT-37)
    allowed_ip_ranges: tuple[str, ...] = ()    # Nouveau (LOT-37)
    retry_jitter: bool = True                  # Nouveau (LOT-37)
    max_backoff_seconds: float = 30.0          # Nouveau (LOT-37)
```

Dans `src/pyingestkit/adapters/http/transport.py` :

```python
_ALLOWED_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "HEAD"})

@dataclass(frozen=True, slots=True)
class HttpRequestV2:
    url: str
    method: str = "GET"                       # Nouveau (LOT-37)
    body: bytes = b""                         # Nouveau (LOT-37)
    headers: tuple[tuple[str, str], ...] = ()
    timeout_seconds: float = 30.0
    max_bytes: int = 128 * 1024 * 1024
    pinned_ip: str | None = None              # Nouveau (LOT-37: Anti-DNS Rebinding)
```

### C. Gestionnaire de Jetons OAuth 2.0 (`src/pyingestkit/adapters/http/oauth.py`)

Module dédié pour l'automatisation du cycle de vie des jetons OAuth 2.0 :

```python
@dataclass(frozen=True, slots=True)
class OAuthToken:
    access_token: str
    token_type: str = "Bearer"
    expires_at: float | None = None
    refresh_token: str | None = None
    scopes: tuple[str, ...] = ()

    def is_expired(self, clock_skew_seconds: float = 60.0) -> bool:
        if self.expires_at is None:
            return False
        return time.time() + clock_skew_seconds >= self.expires_at

    def __repr__(self) -> str:
        return "OAuthToken(access_token='***REDACTED***', token_type=..., is_expired=...)"

class OAuthTokenProvider(Protocol):
    def get_access_token(self, client: HttpClientV2) -> str: ...
    def invalidate(self) -> None: ...

class ClientCredentialsOAuthProvider:
    """Implémentation du flux OAuth 2.0 Client Credentials Grant."""
    ...

class RefreshTokenOAuthProvider:
    """Implémentation du flux OAuth 2.0 Refresh Token Grant."""
    ...

class OAuthTokenManager:
    """Gestionnaire de jetons thread-safe avec cache en mémoire et auto-renouvellement."""
    ...
```

### D. Implémentation du Transport Sécurisé (`_httpx.py`)

Un transport HTTPX personnalisé avec `NetworkBackend` pour `httpcore` :
- Surcharge de `connect_tcp(host, port, timeout, ...)` :
  - Si `request.pinned_ip` est fourni, connecte la socket TCP directement sur cette IP.
  - Sinon, résout l'hôte via `AntiSsrfValidator.resolve_and_validate(host, port)` et connecte la première IP valide.
- Préserve l'appel ultérieur `start_tls(server_hostname=host)` assurant la conformité TLS et la validation stricte des certificats X.509.

---

## 6. Invariants Architecturaux & Sécurité

1. **Isolation Hexagonale Stricte :**
   - Aucune référence à `httpx`, `httpcore`, `socket` ou `ssl` dans `domain/` ou `ports/`.
   - Les contrats du domaine restent entièrement découplés de la technologie de transport.
2. **Neutralité de l'API Publique Racine :**
   - `src/pyingestkit/__init__.py` reste rigoureusement scellé à ses **11 symboles historiques**.
   - `pyingestkit.sources` expose uniquement des composants abstraits.
3. **Zéro Fuite de Secrets (*Credentials Redaction*) :**
   - Aucune valeur de `client_secret`, `access_token` ou `refresh_token` ne doit apparaître dans les diagnostics, métadonnées de ressource, exceptions ou journaux d'exécution.
   - Les représentations `__repr__` et `__str__` de tous les modèles OAuth masquent systématiquement les champs sensibles.
4. **Prise en Compte de l'Incertitude Réseau (`OutcomeUncertainty`) :**
   - En cas d'échec sur timeout ou transport lors d'une requête `POST` ou `PUT`, `FailureEvidence.uncertainty` est positionné à `OutcomeUncertainty.UNCERTAIN`.
   - Pour les requêtes idempotentes `GET` et `HEAD`, `FailureEvidence.uncertainty` reste `OutcomeUncertainty.KNOWN`.

---

## 7. Stratégie de Validation & Tests

1. **Tests Unitaires du Bouclier Anti-SSRF (`tests/unit/v2/test_http_ssrf.py`) :**
   - Validation des détections de plages d'adresses privées (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
   - Validation du blocage loopback (`127.0.0.1`, `localhost`, `::1`).
   - Validation du blocage cloud metadata (`169.254.169.254`).
   - Validation du comportement d'exemption contrôlée (`allow_private_networks=True`, `allowed_ip_ranges`).
2. **Tests Unitaires OAuth 2.0 (`tests/unit/v2/test_http_oauth.py`) :**
   - Simulation d'un serveur d'autorisation OAuth (mock HTTP).
   - Test du cache en mémoire et de la marge de validité (*clock skew*).
   - Test de l'interception automatique d'un `401 Unauthorized`, renouvellement du jeton et rejeu transparent unique.
   - Test de la redaction stricte des secrets dans les logs et `__repr__`.
3. **Tests Unitaires Méthodes & Payloads (`tests/unit/v2/test_http_transport_v2.py`) :**
   - Test de `HttpRequestV2` avec verbes `GET`, `POST`, `PUT`, `HEAD`.
   - Test de la transmission de payload binaire ou JSON.
   - Test de la qualification de l'incertitude (`UNCERTAIN` sur `POST` timeout).
4. **Vérification Globale & Portes Qualité :**
   - `make quality` (Ruff et Mypy stricts : 0 erreur).
   - `make architecture-v2` (79/79 passés).
   - `make test-v2` (> 380 tests passés).
   - `mkdocs build --strict`.
