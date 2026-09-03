# ADR-023 — Retry policy, idempotency and Retry-After

## Status
Accepted for PyIngestKit V0.2.0-a1.

## Context
Transient HTTP failures require retries, but unconditional retries can duplicate side effects or overload a failing service.

## Decision
- `RetryPolicy` is a PyIngestKit-owned contract backed internally by Tenacity.
- Runtime dependency: `tenacity>=9.1.4,<10`.
- Default retry methods are `GET` and `HEAD` only.
- Default retry status codes are `408`, `425`, `429`, `500`, `502`, `503`, `504`.
- Timeouts and transport failures are retryable only when the HTTP method is allowed by the policy.
- `Retry-After` is honored when valid and capped by `max_delay_seconds`.
- Otherwise retry delay uses bounded exponential backoff with optional jitter.
- Default attempts are finite (`3`).
- Tests inject a non-sleeping function so retry tests remain deterministic and fast.

## Consequences
Retry behavior is explicit and conservative. Non-idempotent methods such as POST are not retried by default.
