# ADR-009 — Secret handling policy

**Status:** Accepted for V0.1

## Decision

Secrets are runtime configuration, never artifacts. They must not be written to manifests, logs or serialized run results.
