# ADR-015 — Operational logs vs runtime events

**Status:** Accepted — V0.1.5

Operational logs remain stderr/rotating log-file concerns. Structural lifecycle events are persisted through MetadataStore.

Do not mirror every DEBUG/INFO line into the database. Events such as RUN_STARTED, STEP_SUCCEEDED and RUN_FAILED form the queryable audit trail.
