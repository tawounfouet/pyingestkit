# PyIngestKit V2 — LOT-13 HTTP Acquisition and Provenance

LOT-13 adds the first network acquisition adapter to the V2 execution model.

The domain remains provider-neutral. HTTPX is confined to the adapter
implementation and is not imported by domain/application/runtime code.

## Runtime path

```text
Source.http(...)
      |
      v
SourceRegistry
      |
      v
HttpSourceConnector
      |
      +--> network policy
      |     - HTTPS by default
      |     - explicit host allow-list
      |     - explicit non-default ports
      |     - bounded redirects
      |
      +--> optional credential resolver
      |     - CredentialReference in domain
      |     - secret headers only at runtime
      |     - headers never persisted
      |
      +--> HttpClientV2
      |     - dependency-neutral protocol
      |     - bounded body
      |     - timeout / transport mapping
      |     - retryable status policy
      |
      +--> HttpxHttpClientV2
      |     - provider implementation
      |
      v
AcquisitionResult
      |
      +--> SHA-256
      +--> size
      +--> media type
      +--> safe ResourceReference
      +--> allow-listed HTTP provenance
      |
      v
IngestionRuntime
      |
      v
durable RAW before decode
```

## Network policy

Every connector instance requires an `HttpAccessPolicy` with at least one
allowed hostname.

LOT-13 defaults to HTTPS. Plain HTTP requires an explicit
`allow_http=True`. Non-default ports also require an explicit allow-list.

Redirects are processed by `HttpSourceConnector`, not delegated to the HTTP
client. Every redirect target is validated **before** the next request is sent.
This prevents a permitted URL from silently redirecting acquisition to an
unapproved host or port.

## Credentials

`Source.http(...)` stores only a `CredentialReference`. Secret material is
resolved at runtime through `HttpCredentialResolverV2`.

The resolver may return request headers such as `Authorization`, but those
headers remain transport-local. They are never copied into:

- `AcquisitionResult.source_metadata`;
- `ResourceReference.metadata`;
- `ArtifactReference`;
- diagnostics;
- failure details.

## Provenance boundary

Successful HTTP acquisition records only the following portable values:

- requested URL after persistence-safe sanitization;
- resolved URL after redirects and sanitization;
- HTTP status;
- content type;
- ETag when present;
- Last-Modified when present;
- attempt count;
- redirect count;
- response size;
- SHA-256.

Sensitive query parameters introduced by a redirect are removed before any URL
crosses the persistence boundary.

Arbitrary response headers are not persisted.

## Retry behavior

LOT-13 retries a bounded set of transient statuses plus timeout/transport
failures.

The default retry statuses are:

```text
408 425 429 500 502 503 504
```

`Retry-After` numeric values are honored up to the policy cap. Otherwise
bounded exponential backoff is used.

## Size boundary

`HttpRequestV2.max_bytes` is passed to the transport adapter. The HTTPX
implementation checks both `Content-Length` and streamed body size, aborting
once the configured bound is exceeded.

## Dependency governance

HTTPX remains temporarily present in the base dependency set during the 1.x
maintenance transition because the stable V1 contract freezes the optional-extra
names and clean-wheel qualification still executes historical HTTP jobs.

LOT-13 therefore isolates HTTPX **architecturally** inside the provider adapter,
but does not alter the governed V1 packaging surface. Moving HTTPX behind a
dedicated V2 extra is deferred to the 2.0 package cut.

## Compatibility

V1 remains available unchanged:

```python
from pyingestkit.sources.http import HttpSource
```

V2 callers use:

```python
from pyingestkit.sources.http.v2 import (
    HttpAccessPolicy,
    HttpSourceConnector,
)
```

or the cumulative V2 source namespace:

```python
from pyingestkit.sources.v2 import HttpAccessPolicy, HttpSourceConnector
```

## Deferred

LOT-13 does not introduce:

- POST/PUT ingestion semantics;
- OAuth/token refresh orchestration;
- proxy configuration;
- DNS/IP-level SSRF enforcement beyond explicit host/port policy;
- asynchronous HTTP;
- persisted SQL HTTP provenance;
- provider-specific authentication plugins.

Those concerns require separate contracts rather than implicit behavior.
