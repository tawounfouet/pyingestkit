# ADR-022 — HTTPX as the default HTTP transport

## Status
Accepted for PyIngestKit V0.2.0-a1.

## Context
V0.2 introduces HTTP acquisition. PyIngestKit needs timeout handling, redirects, testable transports and a production-grade synchronous client without turning a third-party response object into the framework contract.

## Decision
- `HttpRequest`, `HttpResponse` and `HttpClient` are PyIngestKit-owned contracts.
- `HttpxClient` is the default synchronous implementation.
- Runtime dependency: `httpx>=0.28.1,<1`.
- `httpx.Response` is never the return type of the framework `HttpClient` contract.
- Tests use `httpx.MockTransport`; no unit/integration test requires Internet access.
- HTTPX 1.0 development prereleases are intentionally excluded until a stable 1.x compatibility decision is made.

## Consequences
HTTP transport can evolve independently from job APIs. HTTPX remains replaceable and contained behind a protocol.
