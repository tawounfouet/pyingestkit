# HTTP acquisition — V0.2.0 Alpha 1

V0.2.0-a1 establishes the transport layer only:

```text
HttpSource
    │
    ▼
HttpClient
    │
    ├── RetryPolicy
    │
    ▼
  HTTPX
```

## Contracts

```text
HttpRequest
HttpResponse
HttpClient
HttpxClient
HttpSource
RetryPolicy
```

`HttpSource.fetch_response()` returns a framework-owned `HttpResponse`.

Alpha 1 intentionally does **not** register an HTTP response as a `RawArtifact`. The next acquisition milestone adds the bridge:

```text
HTTP → immutable RAW → SHA-256 → provenance → manifest/metadata
```

Keeping this boundary explicit avoids implementing parsing or artifact semantics in the transport adapter.

## Defaults

```text
timeout              30 seconds
follow redirects     true
max attempts         3
retry methods        GET, HEAD
retry status         408, 425, 429, 500, 502, 503, 504
backoff               exponential
jitter                enabled
Retry-After           honored and bounded
```

## Secret handling

The framework sanitizes URLs and headers in representations/errors/logging boundaries. In particular, authorization/cookie/API-key headers and secret-looking query values must not be rendered in clear text.

## Offline testing

HTTP tests use `httpx.MockTransport`. CI must never require a live remote endpoint for these tests.
